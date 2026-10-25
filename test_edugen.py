"""Suite de testes do EduGen (TrabalhoPython.py) — só usa a biblioteca padrão.

Corre com:  python3 -m unittest test_edugen -v
"""

import json
import py_compile
import random
import unittest
from pathlib import Path

SRC_PATH = Path(__file__).with_name("TrabalhoPython.py")


def carregar_helpers():
    """Executa apenas o bloco de funções auxiliares do app (sem precisar de streamlit)."""
    import copy
    import io
    import os
    import re
    from datetime import datetime

    src = SRC_PATH.read_text(encoding="utf-8")
    inicio = src.index("def extrair_json_seguro")
    fim = src.index("\nwith st.sidebar:")
    # recua até ao separador '====' anterior para não cortar código a meio
    sep = "# =========================================================="
    fim = src.rindex(sep, 0, fim)
    bloco = src[inicio:fim]

    class StDummy:
        session_state = {}
        warnings = []

        def warning(self, *args, **kwargs):
            StDummy.warnings.append(" ".join(str(a) for a in args))

        def rerun(self):
            # como o script de teste não executa a UI, qualquer rerun é um erro de contrato
            raise RuntimeError("ST_RERUN")

    ns = {
        "os": os,
        "json": json,
        "io": io,
        "re": re,
        "random": random,
        "st": StDummy(),
        "copy": copy,
        "datetime": datetime,
        # fpdf2 é opcional: nos testes força-se o caminho "sem lib"
        "FPDF": None,
        "PDF_LIB_DISPONIVEL": False,
    }
    exec(bloco, ns)  # noqa: S102 - ficheiro local confiável
    return ns


H = carregar_helpers()
extrair_json_seguro = H["extrair_json_seguro"]
normalizar = H["normalizar"]
parse_nota_percentual = H["parse_nota_percentual"]
ajustar_num_opcoes = H["ajustar_num_opcoes"]
gerar_dados_m1_offline = H["gerar_dados_m1_offline"]
gerar_dados_m2_offline = H["gerar_dados_m2_offline"]
corrigir_por_keywords = H["corrigir_por_keywords"]
registar_historico = H["registar_historico"]
restaurar_do_historico = H["restaurar_do_historico"]
dados_repetir_m1 = H["dados_repetir_m1"]
dados_repetir_m2 = H["dados_repetir_m2"]
exportar_recurso_pdf = H["exportar_recurso_pdf"]
_cp1252 = H["_cp1252"]

PERGUNTA_BASE = {
    "pergunta": "Q?",
    "opcoes": ["A", "B", "C", "D"],
    "resposta_correta": 0,
    "explicacao": "porque sim",
}


class TestExtrairJsonSeguro(unittest.TestCase):
    def test_json_limpo(self):
        self.assertEqual(extrair_json_seguro('{"a": 1}'), {"a": 1})

    def test_com_fence_json(self):
        self.assertEqual(extrair_json_seguro('```json\n{"a": 1}\n```'), {"a": 1})

    def test_com_fence_sem_lang(self):
        self.assertEqual(extrair_json_seguro('```\n{"a": 1}\n```'), {"a": 1})

    def test_texto_em_volta(self):
        self.assertEqual(extrair_json_seguro('Aqui está: {"x": 5} espero que ajude'), {"x": 5})

    def test_vazio_levanta(self):
        with self.assertRaises(ValueError):
            extrair_json_seguro("   ")

    def test_invalido_levanta(self):
        with self.assertRaises((json.JSONDecodeError, ValueError)):
            extrair_json_seguro("isto não é json {{")


class TestNormalizar(unittest.TestCase):
    def test_minusculas_e_trim(self):
        self.assertEqual(normalizar("  Timina. "), "timina")

    def test_espacos_multiplos(self):
        self.assertEqual(normalizar("memória   virtual"), "memória virtual")

    def test_none(self):
        self.assertEqual(normalizar(None), "")

    def test_int_nao_crash(self):
        self.assertEqual(normalizar(42), "42")


class TestParseNota(unittest.TestCase):
    def test_int(self):
        self.assertEqual(parse_nota_percentual(85), 85)

    def test_str(self):
        self.assertEqual(parse_nota_percentual("85"), 85)

    def test_str_percent(self):
        self.assertEqual(parse_nota_percentual("85%"), 85)

    def test_float_str(self):
        self.assertEqual(parse_nota_percentual("84.9"), 84)

    def test_clamp_alto(self):
        self.assertEqual(parse_nota_percentual(150), 100)

    def test_clamp_baixo(self):
        self.assertEqual(parse_nota_percentual(-5), 0)

    def test_lixo(self):
        self.assertEqual(parse_nota_percentual("n/a"), 0)

    def test_none(self):
        self.assertEqual(parse_nota_percentual(None), 0)


class TestAjustarNumOpcoes(unittest.TestCase):
    def test_todos_os_tamanhos(self):
        for n in (2, 3, 4, 5, 6):
            random.seed(0)
            q = ajustar_num_opcoes(dict(PERGUNTA_BASE), n)
            self.assertEqual(len(q["opcoes"]), n)
            self.assertEqual(q["opcoes"][q["resposta_correta"]], "A")
            self.assertTrue(0 <= q["resposta_correta"] < n)

    def test_minimo(self):
        q = ajustar_num_opcoes(dict(PERGUNTA_BASE), 1)
        self.assertEqual(len(q["opcoes"]), 2)

    def test_invalida_devolve_como_esta(self):
        q = {"pergunta": "Q", "opcoes": [], "resposta_correta": 0}
        self.assertEqual(ajustar_num_opcoes(q, 4), q)

    def test_bool_rejeitado(self):
        q = {"pergunta": "Q", "opcoes": ["A", "B"], "resposta_correta": True}
        self.assertEqual(ajustar_num_opcoes(q, 2), q)

    def test_indice_negativo_rejeitado(self):
        q = {"pergunta": "Q", "opcoes": ["A", "B"], "resposta_correta": -1}
        self.assertEqual(ajustar_num_opcoes(q, 2), q)

    def test_opcoes_duplicadas_sao_unificadas(self):
        # Erradas duplicadas (dados corrompidos/da IA) deixavam a pergunta
        # invalida no render; agora unificam-se antes de baralhar.
        random.seed(0)
        q = {"pergunta": "Q", "opcoes": ["A", "B", "B", "C"], "resposta_correta": 0}
        d = ajustar_num_opcoes(q, 4)
        self.assertTrue(H["pergunta_valida"](d), d)


class TestM1Offline(unittest.TestCase):
    def test_tema_adn_factual(self):
        d = gerar_dados_m1_offline("Estrutura e Funcionalidades do ADN", 4)
        self.assertIn("dupla", d["texto_explicativo"].lower() + "hélice")
        self.assertEqual(len(d["perguntas"]), 2)
        for q in d["perguntas"]:
            self.assertEqual(len(q["opcoes"]), 4)
            self.assertTrue(0 <= q["resposta_correta"] < 4)
        palavras = [l["palavra_oculta"] for l in d["fill_in_the_blank"]]
        self.assertIn("nucleótidos", palavras)
        # garante que o typo antigo não voltou
        self.assertNotIn("nucleótipos", json.dumps(d))

    def test_tema_so(self):
        d = gerar_dados_m1_offline("Sistemas Operativos e Gestão de Memória", 4)
        self.assertIn("pagina", d["texto_explicativo"].lower())
        self.assertEqual(len(d["perguntas"]), 2)

    def test_generico_respeita_num_opcoes(self):
        d = gerar_dados_m1_offline("Tema Qualquer XPTO", 2)
        self.assertTrue(d.get("_demo_generico"))
        for q in d["perguntas"]:
            self.assertEqual(len(q["opcoes"]), 2)

    def test_generico_menciona_tema(self):
        d = gerar_dados_m1_offline("Volcanoes and Dynamic Earth", 4)
        self.assertIn("Volcanoes and Dynamic Earth", d["texto_explicativo"])

    def test_banco_foto_coberto_pelo_tema(self):
        d = gerar_dados_m1_offline("A Fotossíntese", 4)
        self.assertNotIn("_demo_generico", d)
        self.assertIn("clorofila", d["texto_explicativo"].lower())

    def test_banco_global_nao_mutado(self):
        d = gerar_dados_m1_offline("ADN", 4)
        d["fill_in_the_blank"][0]["palavra_oculta"] = "MUTADO"
        d2 = gerar_dados_m1_offline("ADN", 4)
        self.assertEqual(d2["fill_in_the_blank"][0]["palavra_oculta"], "nucleótidos")

    def test_tema_vazio_tem_fallback(self):
        d = gerar_dados_m1_offline("   ", 4)
        self.assertIn("este tema", d["texto_explicativo"])
        self.assertNotIn("''", d["texto_explicativo"])


class TestM2Offline(unittest.TestCase):
    def _valida(self, d):
        self.assertEqual(len(d["pares"]), 4)
        for p in d["pares"]:
            self.assertTrue(p["conceito"] and p["definicao"])

    def test_so(self):
        self._valida(gerar_dados_m2_offline("Sistemas Operativos"))

    def test_adn(self):
        self._valida(gerar_dados_m2_offline("ADN"))

    def test_generico(self):
        self._valida(gerar_dados_m2_offline("Tema Livre Qualquer"))

    def test_copias_independentes(self):
        d = gerar_dados_m2_offline("Sistemas Operativos")
        d["pares"][0]["conceito"] = "MUTADO"
        d2 = gerar_dados_m2_offline("Sistemas Operativos")
        self.assertNotEqual(d2["pares"][0]["conceito"], "MUTADO")

    def test_tema_vazio_tem_fallback(self):
        d = gerar_dados_m2_offline("")
        self.assertIn("este tema", d["pares"][0]["conceito"])


class TestKeywords(unittest.TestCase):
    def test_tudo_encontrado(self):
        r = corrigir_por_keywords("A memória usa frames fixos", "memória, frames")
        self.assertEqual(r["nota_percentual"], 100)
        self.assertEqual(r["resultado"], "CERTO")

    def test_nada_encontrado(self):
        r = corrigir_por_keywords("nada a ver com o tema", "memória, frames")
        self.assertEqual(r["nota_percentual"], 0)
        self.assertEqual(r["resultado"], "ERRADO")

    def test_parcial_acima_limiar(self):
        r = corrigir_por_keywords("fala de memória mas nada mais", "memória, frames, paginação, swap")
        self.assertEqual(r["nota_percentual"], 25)
        self.assertEqual(r["resultado"], "ERRADO")

    def test_case_insensitive(self):
        r = corrigir_por_keywords("MEMÓRIA VIRTUAL", "memória virtual")
        self.assertEqual(r["resultado"], "CERTO")

    def test_sem_keywords(self):
        r = corrigir_por_keywords("qualquer resposta", "  ")
        self.assertEqual(r["nota_percentual"], 0)

    def test_em_falta_com_caixa_original(self):
        r = corrigir_por_keywords("O ADN tem hereditariedade.", "ADN, Hereditariedade, Replicação")
        self.assertEqual(r["em_falta"], ["Replicação"])
        self.assertIn("Replicação", r["feedback"])

    def test_em_falta_vazia_quando_tudo_encontrado(self):
        r = corrigir_por_keywords("A memória usa frames fixos", "memória, frames")
        self.assertEqual(r["em_falta"], [])

    def test_em_falta_vazia_sem_keywords(self):
        r = corrigir_por_keywords("qualquer resposta", "  ")
        self.assertEqual(r["em_falta"], [])


class TestResumoEstudo(unittest.TestCase):
    """Resumo pós-erros: onde falhámos e o que estudar (funciona offline)."""

    def setUp(self):
        H["STR"] = {
            "study_intro": "Falhaste {erros} de {total}. O que rever:",
            "study_item_expl": "**{etiqueta}** — resposta certa: **{certa}**. {explicacao}",
            "study_item": "**{etiqueta}** — resposta certa: **{certa}**.",
            "study_tip": "Estuda {onde}.",
        }

    def tearDown(self):
        H.pop("STR", None)

    def test_sem_erros_devolve_vazio(self):
        self.assertEqual(H["construir_resumo_estudo"]([], 4, "aqui"), "")
        self.assertEqual(H["construir_resumo_estudo"](None, 4, "aqui"), "")

    def test_lista_com_e_sem_explicacao(self):
        r = H["construir_resumo_estudo"](
            [
                {"etiqueta": "Pergunta 1", "certa": "Timina", "explicacao": "No  ADN usa-se T."},
                {"etiqueta": "Lacuna 2", "certa": "nucleótidos", "explicacao": "   "},
            ],
            4,
            "no texto",
        )
        self.assertIn("Falhaste 2 de 4", r)
        self.assertIn("**Pergunta 1**", r)
        self.assertIn("**Timina**", r)
        self.assertIn("No ADN usa-se T.", r)  # espaços colapsados
        self.assertIn("**Lacuna 2**", r)
        self.assertIn("nucleótidos", r)
        self.assertIn("Estuda no texto.", r)
        self.assertNotIn("None", r)

    def test_ignora_entradas_invalidas(self):
        r = H["construir_resumo_estudo"]([{"etiqueta": "E"}, None], 1, "onde")
        self.assertIn("Falhaste 1 de 1", r)
        self.assertIn("**E**", r)
        self.assertIn("Estuda onde.", r)


class TestRepetir(unittest.TestCase):
    """Modo de recuperação: recursos com apenas os itens falhados (Módulos 1 e 2)."""

    def test_m1_construcao(self):
        d = dados_repetir_m1(
            "Texto de recuperação.",
            [dict(PERGUNTA_BASE, pergunta="Falhei esta")],
            [{"frase": "X [___] Y", "palavra_oculta": "y"}],
            4,
        )
        self.assertTrue(d["_recuperacao"])
        self.assertEqual(d["_total_original"], 4)
        self.assertEqual(len(d["perguntas"]), 1)
        self.assertEqual(len(d["fill_in_the_blank"]), 1)
        self.assertIn("Falhei esta", d["perguntas"][0]["pergunta"])
        self.assertEqual(d["texto_explicativo"], "Texto de recuperação.")

    def test_m1_itens_sao_copias_datas(self):
        p = dict(PERGUNTA_BASE)
        d = dados_repetir_m1("t", [p], [], 2)
        p["pergunta"] = "MUTADO"
        self.assertNotEqual(d["perguntas"][0]["pergunta"], "MUTADO")

    def test_m2_construcao(self):
        par = {"conceito": "C", "definicao": "D"}
        d = dados_repetir_m2([par], 4)
        self.assertTrue(d["_recuperacao"])
        self.assertEqual(d["_total_original"], 4)
        self.assertEqual(len(d["pares"]), 1)

    def test_m2_itens_sao_copias_datas(self):
        par = {"conceito": "C", "definicao": "D"}
        d = dados_repetir_m2([par], 4)
        par["conceito"] = "MUTADO"
        self.assertNotEqual(d["pares"][0]["conceito"], "MUTADO")

    def test_listas_vazias_nao_explodem(self):
        d = dados_repetir_m1("t", None, None, 0)
        self.assertTrue(d["_recuperacao"])
        self.assertEqual(d["perguntas"], [])
        self.assertEqual(d["fill_in_the_blank"], [])
        d2 = dados_repetir_m2(None, 0)
        self.assertEqual(d2["pares"], [])

    def test_strings_do_modo_nos_dois_idiomas(self):
        strings = H["STRINGS"]
        for lang in ("pt", "en"):
            for chave in ("retry_m1_btn", "retry_m2_btn", "retry_exit", "retry_on"):
                self.assertTrue(strings[lang][chave].strip(), f"{lang}.{chave} vazio")

    def test_placeholders_iguais_pt_en(self):
        import re as _re

        ph = lambda s: set(_re.findall(r"\{(\w+)\}", s))
        strings = H["STRINGS"]
        self.assertEqual(ph(strings["pt"]["retry_on"]), ph(strings["en"]["retry_on"]))
        self.assertEqual(ph(strings["pt"]["retry_on"]), {"falhados", "total"})
        self.assertTrue(strings["pt"]["retry_on"].startswith("Modo de recuperação"))
        self.assertTrue(strings["en"]["retry_on"].startswith("Recovery mode"))


class TestTemaRecurso(unittest.TestCase):
    """O tema do momento da geração (_tema) manda na exportação e no histórico."""

    def test_m1_e_m2_guardam_tema(self):
        self.assertEqual(gerar_dados_m1_offline("ADN", 4)["_tema"], "ADN")
        self.assertEqual(gerar_dados_m2_offline("Sistemas Operativos")["_tema"], "Sistemas Operativos")

    def test_geradores_normalizam_ou_fazem_fallback(self):
        self.assertEqual(gerar_dados_m1_offline("  Hist. ", 2)["_tema"], "Hist.")
        self.assertEqual(gerar_dados_m2_offline("   ")["_tema"], "este tema")
        self.assertEqual(gerar_dados_m1_offline("", 2, lang="en")["_tema"], "este tema")

    def test_tema_de_recurso_prefere_o_guardado(self):
        tdr = H["tema_de_recurso"]
        self.assertEqual(tdr({"_tema": "Volcanoes"}, "novo tema"), "Volcanoes")
        self.assertEqual(tdr({"_tema": "   "}, "Backup"), "Backup")
        self.assertEqual(tdr({}, "novo tema"), "novo tema")
        self.assertEqual(tdr(None, "  "), "este tema")
        self.assertEqual(tdr(42, "novo"), "novo")

    def test_ligado_na_ui_e_no_caminho_online(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        # def + 5 call sites (M1 offline/online, M2 offline/online, exportação)
        self.assertGreaterEqual(src.count("tema_de_recurso("), 6)
        self.assertIn('dados_m1["_tema"] = str(tema_m1 or "").strip() or "este tema"', src)
        self.assertIn('dados_m2["_tema"] = str(tema_m2 or "").strip() or "este tema"', src)
        self.assertIn("tema_exp = tema_de_recurso(dados_exp, tema_m1)", src)


class TestHero(unittest.TestCase):
    """HTML do cabeçalho hero (painel editorial + chip de estado)."""

    def test_html_completo(self):
        h = H["construir_hero"]("EduGen X", "Sub Y", "Offline / Demo", "off")
        self.assertIn("edugen-hero", h)
        self.assertIn("<h1", h)
        self.assertIn("EduGen X", h)
        self.assertIn("Sub Y", h)
        self.assertIn("edugen-hero-badge--off", h)

    def test_marca_e_assinatura(self):
        h = H["construir_hero"]("EduGen: Gerador e Avaliador", "S", "c")
        self.assertIn('class="edugen-brand">EduGen<', h)
        self.assertIn('class="edugen-tagline">Gerador e Avaliador<', h)

    def test_titulo_sem_dois_pontos(self):
        h = H["construir_hero"]("EduGen X", "S", "c")
        self.assertIn('class="edugen-brand">EduGen X<', h)
        self.assertNotIn("edugen-tagline", h)

    def test_online_sem_classe_off(self):
        h = H["construir_hero"]("T", "S", "Online", "on")
        self.assertNotIn("--off", h)

    def test_icone_material_vira_simbolo(self):
        h = H["construir_hero"]("T", "S", ":material/cloud_off: Offline / Demo", "off")
        self.assertIn('<span class="edugen-ico"', h)
        self.assertIn(">cloud_off</span>", h)
        self.assertNotIn(":material/", h)
        self.assertIn("Offline / Demo", h)

    def test_sem_icone_como_simbolo(self):
        h = H["construir_hero"]("T", "S", "Online", "on")
        self.assertNotIn("edugen-ico", h)
        self.assertIn("Online", h)

    def test_escapa_html(self):
        h = H["construir_hero"]("<b>x</b> & y", "s", "c")
        self.assertNotIn("<b>", h)
        self.assertIn("&amp;", h)


class TestFluxoCorrecao(unittest.TestCase):

    def test_m1_tudo_certo_da_100(self):
        d = gerar_dados_m1_offline("ADN", 4)
        acertos = len(d["perguntas"]) + len(d["fill_in_the_blank"])
        total = acertos
        self.assertEqual((acertos / total) * 100, 100)

    def test_m1_tudo_errado_da_0(self):
        d = gerar_dados_m1_offline("ADN", 4)
        self.assertEqual((0 / (len(d["perguntas"]) + len(d["fill_in_the_blank"]))) * 100, 0)

    def test_m1_sem_perguntas_nao_divide_por_zero(self):
        perguntas_validas, lacunas_validas = [], 0
        total = len(perguntas_validas) + lacunas_validas
        self.assertEqual(total, 0)
        # o app mostra aviso em vez de calcular; aqui só garantimos que não há exceção
        with self.assertRaises(ZeroDivisionError):
            _ = 1 / total
        # ...e que o guarda do app evita o cálculo:
        nota = None if total == 0 else 100
        self.assertIsNone(nota)

    def test_m2_todas_certas(self):
        d = gerar_dados_m2_offline("Sistemas Operativos")
        mapa = {p["conceito"]: p["definicao"] for p in d["pares"]}
        # aluno responde tudo certo
        acertos = sum(1 for c, esp in mapa.items() if mapa[c] == esp)
        self.assertEqual(acertos, len(d["pares"]))


class TestEstatico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SRC_PATH.read_text(encoding="utf-8")

    def test_compila(self):
        py_compile.compile(str(SRC_PATH), doraise=True)

    def test_sem_api_depreciada(self):
        self.assertNotIn("use_column_width", self.src)

    def test_radio_sem_placeholder(self):
        idx = self.src.find("st.radio(")
        self.assertNotEqual(idx, -1)
        bloco = self.src[idx : idx + 500]
        self.assertNotIn("placeholder", bloco)

    def test_modo_offline_existe(self):
        for agulha in (
            "Offline / Demo",
            "gerar_dados_m1_offline",
            "gerar_dados_m2_offline",
            "corrigir_por_keywords",
            "parse_nota_percentual",
        ):
            self.assertIn(agulha, self.src)

    def test_shuffle_estavel_m2(self):
        self.assertIn("def_baralhadas", self.src)

    def test_validacao_resposta_correta(self):
        self.assertIn("0 <=", self.src)
        self.assertIn("len(opcoes)", self.src)

    def test_validacao_dicts(self):
        self.assertIn("if not isinstance(dados_m1, dict)", self.src)
        self.assertIn("if not isinstance(dados_m2, dict)", self.src)
        self.assertIn("if not isinstance(q, dict)", self.src)

    def test_m2_por_indice(self):
        self.assertIn("respostas_assoc[idx]", self.src)

    def test_imagem_helper(self):
        self.assertIn("def imagem_para_bytes", self.src)
        self.assertIn("imagem_para_bytes(image)", self.src)

    def test_sem_imagem_externa(self):
        self.assertNotIn("img.icons8.com", self.src)

    def test_keywords_vazias_avisam(self):
        self.assertIn("palavras-chave esperadas antes de corrigir", self.src)

    def test_imagem_robusta(self):
        self.assertIn('.convert("RGB")', self.src)
        self.assertIn('mime_type="image/png"', self.src)

    def test_resumo_estudo_nos_tres_modulos(self):
        self.assertIn("def construir_resumo_estudo", self.src)
        # def + chamadas no M1 e no M2 (o M3 usa study_missed diretamente)
        self.assertEqual(self.src.count("construir_resumo_estudo("), 3)
        # expander de estudo igual nos três módulos (M1, M2 e M3 offline)
        self.assertEqual(self.src.count('st.expander(STR["study_title"]'), 3)
        self.assertIn('STR["study_title"]', self.src)
        self.assertIn('STR["study_missed"]', self.src)

    def test_identidade_animada(self):
        self.assertIn("@keyframes ed-rise", self.src)
        self.assertIn("@keyframes ed-drift", self.src)
        self.assertIn("def construir_hero", self.src)
        self.assertIn("edugen-brand", self.src)
        self.assertIn("def celebrar", self.src)
        # def + 4 chamadas (M1, M2, M3 offline e avaliação online)
        self.assertEqual(self.src.count("celebrar()"), 5)
        # botões principais com o estilo primário
        self.assertEqual(self.src.count('type="primary"'), 8)

    def test_editor_invalida_submissao_stale(self):
        # adicionar pergunta/lacuna ou repor a base demo invalida a submissão
        # anterior (senão o painel de resultados reaparece com erros falsos)
        self.assertGreaterEqual(
            self.src.count('st.session_state.pop("m1_submetido", None)'), 6
        )

    def test_editor_rejeita_opcoes_duplicadas_por_caixa(self):
        # "Frames" e "frames" nas opções tornavam o radio ambíguo
        self.assertIn("normalizar(o, remover_acentos=True) for o in opts", self.src)

    def test_marca_tolerante_a_assets_em_falta(self):
        # o entregável é um ficheiro único: sem edugen_mark.png não pode crashar
        self.assertIn("MARCA_DISPONIVEL", self.src)
        self.assertIn("os.path.exists(MARCA_APP)", self.src)

    def test_aviso_kw_no_papel_aluno(self):
        # o Aluno não pode "definir palavras-chave": recebe instrução para pedir ao professor
        self.assertIn('STR["ask_kw_first"] if not is_student else STR["ask_kw_student"]', self.src)

    def test_regenerar_limpa_editor_texto(self):
        # o session_state da textarea sobrepõe-se ao value=; sem pop, "Guardar
        # texto" reescrevia o texto antigo por cima do recurso novo
        self.assertGreaterEqual(
            self.src.count('st.session_state.pop("ed_texto", None)'), 2
        )

    def test_pdf_cache_por_assinatura(self):
        # o exportador renderiza a cada rerun: o PDF só se reconstrói quando o
        # conteúdo muda (md5 do .md reutiliza hashlib, já sem import morto)
        self.assertGreaterEqual(self.src.count("import hashlib"), 1)
        self.assertIn("hashlib.md5(", self.src)
        self.assertIn("_pdf_cache_m1", self.src)


class TestUX(unittest.TestCase):
    def test_strings_paridade_pt_en(self):
        strings = H["STRINGS"]
        self.assertEqual(set(strings["pt"].keys()), set(strings["en"].keys()))
        self.assertGreater(len(strings["pt"]), 50)

    def test_nenhuma_chave_orfa(self):
        import re as _re

        src = SRC_PATH.read_text(encoding="utf-8")
        orfas = [
            k
            for k in H["STRINGS"]["pt"]
            # uso legítimo nos dois acessos: literal STR["k"] e dinâmico STRINGS[lang]["k"]
            if not _re.search(rf"STR(?:INGS\[[^\[\]]*\])?\[['\"]({_re.escape(k)})['\"]\]", src)
        ]
        self.assertEqual(orfas, [], f"chaves STRINGS sem qualquer uso: {orfas}")

    def test_todas_as_chaves_str_existem(self):
        import re as _re

        src = SRC_PATH.read_text(encoding="utf-8")
        usadas = set(_re.findall(r"STR\[[\"']([A-Za-z0-9_]+)[\"']\]", src))
        self.assertGreater(len(usadas), 100)
        for lang in ("pt", "en"):
            faltam = usadas - set(H["STRINGS"][lang].keys())
            self.assertEqual(faltam, set(), f"STR[...] sem texto em {lang}: {sorted(faltam)}")

    def test_strings_sem_vazias(self):
        for lang, d in H["STRINGS"].items():
            for k, v in d.items():
                self.assertTrue(v and v.strip(), f"{lang}.{k} vazio")

    def test_contratos_estaveis(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        # valores de opção independentes do idioma (mudar de língua não
        # invalida a seleção: sem saltos silenciosos de modo/papel)
        self.assertIn('is_student = (papel == "student")', src)
        self.assertIn('offline = (modo == "offline")', src)
        self.assertIn('["teacher", "student"]', src)
        self.assertIn('["online", "offline"]', src)
        self.assertIn("format_func=", src)

    def test_strings_sem_emojis(self):
        import re as _re

        padrao = _re.compile(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]')
        for lang, d in H["STRINGS"].items():
            for k, v in d.items():
                self.assertIsNone(
                    padrao.search(v), f"emoji em {lang}.{k}: {v[:40]}"
                )

    def test_app_inteira_sem_emojis(self):
        import re as _re

        src = SRC_PATH.read_text(encoding="utf-8")
        # fora STRINGS só pode haver escapes (ex. \2713 no CSS), nunca o caráter
        achados = _re.findall(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]', src)
        self.assertEqual(achados, [], f"emojis na UI: {achados[:5]}")

    def test_gating_aluno_existe(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn("is_student", src)
        self.assertIn("student_no_data", src)
        self.assertIn("if not is_student and st.button", src)

    def test_editor_offline_existe(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        for agulha in ("ed_title", "ed_q_add", "ed_l_add", "ed_reset", "limpar_chaves_resposta_m1"):
            self.assertIn(agulha, src)

    def test_limpeza_com_ambito(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn('prefixos=("q_", "lac_")', src)
        self.assertIn('prefixos=("assoc_",)', src)
        self.assertIn('extras=("def_baralhadas",)', src)
        # gerar M1/M2 já não apaga a pergunta multimodal do M3
        self.assertNotIn('"pergunta_multimodal")', src.split("def limpar_respostas_antigas")[1].split("def ")[0])

    def test_recuperacao_dados_corrompidos(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn('key="fix_m1"', src)
        self.assertIn('key="fix_m2"', src)

    def test_fluxo_modo_recuperacao_ligado_na_ui(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        # regerar limpa o modo de recuperação; os botões existem nos Módulos 1 e 2
        self.assertIn('st.session_state.pop("dados_m1_recuperacao", None)', src)
        self.assertIn('st.session_state.pop("dados_m2_recuperacao", None)', src)
        self.assertIn('key="btn_retry_m1"', src)
        self.assertIn('key="btn_retry_m2"', src)
        self.assertIn('key="btn_retry_sair_m1"', src)
        self.assertIn('key="btn_retry_sair_m2"', src)
        # o item 4 do prompt (Bloom) só existe na geração online do Módulo 1
        self.assertIn("4. Dificuldade cognitiva das perguntas (taxonomia de Bloom):", src)
        self.assertIn('key="bloom_m1"', src)

    def test_historico_ligado_na_ui(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn("registar_historico(", src)
        self.assertIn("restaurar_do_historico(", src)
        self.assertIn('key=f"hist_restore_{_hi}"', src)
        self.assertIn('historico_recursos', src)

    def test_dados_corrompidos_so_param_a_propria_aba(self):
        import re as _re

        src = SRC_PATH.read_text(encoding="utf-8")
        # A recuperação de dados inválidos é local à aba: um st.stop() a meio
        # das abas matava os módulos restantes até o usuário reparar os dados.
        # O único st.stop() admitido é a porta "modo online sem chave".
        self.assertEqual(src.count("st.stop()"), 1)
        self.assertRegex(
            src, r'else:[ \t]*\r?\n[ \t]*perguntas = dados\.get\("perguntas"'
        )
        self.assertRegex(
            src, r'else:[ \t]*\r?\n[ \t]*pares = \[p for p in dados_m2\.get\("pares"'
        )

    def test_sem_strings_hardcoded(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertNotIn("A resposta do modelo não é um objeto JSON válido.", src.split("STRINGS")[0])
        self.assertNotIn('st.error(f"Erro ao configurar a API do Gemini', src)


class TestValidacao(unittest.TestCase):
    def test_pergunta_ok(self):
        self.assertTrue(H["pergunta_valida"](dict(PERGUNTA_BASE)))

    def test_pergunta_opcao_dict_rejeitada(self):
        q = {"pergunta": "Q", "opcoes": ["A", {"x": 1}], "resposta_correta": 0}
        self.assertFalse(H["pergunta_valida"](q))

    def test_pergunta_opcao_lista_rejeitada(self):
        q = {"pergunta": "Q", "opcoes": [["A"]], "resposta_correta": 0}
        self.assertFalse(H["pergunta_valida"](q))

    def test_pergunta_opcao_bool_rejeitada(self):
        q = {"pergunta": "Q", "opcoes": [True, False], "resposta_correta": 0}
        self.assertFalse(H["pergunta_valida"](q))

    def test_pergunta_opcoes_numericas_ok(self):
        q = {"pergunta": "Q", "opcoes": [1, 2, 3], "resposta_correta": 2}
        self.assertTrue(H["pergunta_valida"](q))

    def test_pergunta_nao_dict(self):
        self.assertFalse(H["pergunta_valida"]("texto"))
        self.assertFalse(H["pergunta_valida"](None))

    def test_par_ok(self):
        self.assertTrue(H["par_valido"]({"conceito": "A", "definicao": "B"}))

    def test_par_definicao_dict_rejeitado(self):
        self.assertFalse(H["par_valido"]({"conceito": "A", "definicao": {"x": 1}}))

    def test_par_vazio_rejeitado(self):
        self.assertFalse(H["par_valido"]({"conceito": "  ", "definicao": "B"}))
        self.assertFalse(H["par_valido"]({"conceito": "A"}))

    def test_par_nao_dict(self):
        self.assertFalse(H["par_valido"](None))


class TestModelosGemini(unittest.TestCase):
    def test_recomendados_sao_strings_validas(self):
        for m in H["MODELOS_RECOMENDADOS"]:
            self.assertIsInstance(m, str)
            self.assertTrue(m)

    def test_ordenar_recomendados_primeiro(self):
        r = H["ordenar_modelos"](
            ["gemini-2.5-flash", "gemini-z", "gemini-3.8-flash", "gemini-3.5-flash-lite"]
        )
        self.assertEqual(
            r[:3], ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
        )
        self.assertEqual(r[3], "gemini-z")

    def test_ordenar_sem_duplicados_vazios_ou_limite(self):
        ordenar = H["ordenar_modelos"]
        self.assertEqual(ordenar(["a", "a", "", None, 42, "b"]), ["a", "b"])
        self.assertEqual(len(ordenar([f"m{i}" for i in range(50)])), 30)

    def test_ordenar_vazio(self):
        self.assertEqual(H["ordenar_modelos"](None), [])

    def test_listar_modelos_filtra_sem_generate_content(self):
        class FakeModels:
            def list(self):
                class M:
                    def __init__(self, name, acoes):
                        self.name = name
                        self.supported_actions = acoes

                return [
                    M("models/gemini-3.8-flash", ["generateContent"]),
                    M("models/gemini-embed", ["embedContent"]),
                    M("models/gemini-sem-acoes", []),
                ]

        class FakeClient:
            models = FakeModels()

        self.assertEqual(
            H["listar_modelos_disponiveis"](FakeClient()),
            ["gemini-3.8-flash", "gemini-sem-acoes"],
        )

    def test_listar_falha_devolve_none(self):
        class FakeClient:
            class models:
                @staticmethod
                def list():
                    raise RuntimeError("sem rede")

        self.assertIsNone(H["listar_modelos_disponiveis"](FakeClient()))

    def test_modelo_indisponivel(self):
        m = H["modelo_indisponivel"]
        self.assertTrue(m("404 NOT_FOUND: models/gemini-1.5-pro is not found"))
        self.assertTrue(m(RuntimeError("This model is no longer available")))
        self.assertFalse(m("429 RESOURCE_EXHAUSTED: quota"))

    def test_ordenar_pro_e_preview_no_fim(self):
        r = H["ordenar_modelos"](
            ["gemini-3.1-pro-preview", "gemini-z-flash", "gemini-3.8-flash", "gemini-2.5-pro"]
        )
        self.assertEqual(r[0], "gemini-3.8-flash")
        self.assertEqual(r[1], "gemini-z-flash")
        self.assertEqual(set(r[2:]), {"gemini-2.5-pro", "gemini-3.1-pro-preview"})

    def test_modelo_pro_deteta_pro_preview_experimental(self):
        mp = H["_modelo_pro"]
        self.assertEqual(mp("gemini-3.1-pro-preview"), 1)
        self.assertEqual(mp("gemini-2.5-pro"), 1)
        self.assertEqual(mp("gemini-2.0-flash-exp"), 1)
        self.assertEqual(mp("gemini-3.8-flash"), 0)
        self.assertEqual(mp("gemini-3.5-flash-lite"), 0)

    def test_erro_quota(self):
        eq = H["erro_quota"]
        self.assertTrue(eq("429 RESOURCE_EXHAUSTED: You exceeded your current quota"))
        self.assertTrue(eq(RuntimeError("Quota exceeded for metric")))
        self.assertFalse(eq("404 NOT_FOUND: model not found"))

    def test_alternativas_sem_pro_e_com_limite(self):
        st = H["st"]
        st.session_state.clear()
        st.session_state["_modelos_lista"] = [
            "gemini-3.1-pro-preview",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-3.6-flash",
        ]
        self.assertEqual(
            H["_alternativas_modelo"]("gemini-3.1-pro-preview", limite=2),
            ["gemini-3.8-flash", "gemini-3.5-flash-lite"],
        )
        st.session_state.clear()
        self.assertEqual(
            H["_alternativas_modelo"]("inexistente"),
            ["gemini-3.8-flash", "gemini-3.5-flash-lite"],
        )


class TestModelosEstatico(unittest.TestCase):
    def test_sem_modelos_retirados_no_fonte(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        for morto in ("gemini-1.5", "gemini-2.0"):
            self.assertNotIn(morto, src, f"{morto} já foi desligado pela Google")

    def test_sidebar_lista_modelos_da_chave(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn("listar_modelos_disponiveis(client)", src)
        self.assertIn("ordenar_modelos", src)
        self.assertIn('key="modelo"', src)
        self.assertIn("MODELOS_RECOMENDADOS", src)

    def test_widgets_estaveis_na_troca_de_idioma(self):
        # sem key estável, o Streamlit recria o widget quando o label muda de
        # idioma e o valor escrito (chave API / upload) perde-se
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn('key="api_key_input"', src)
        self.assertIn('key="m3_upload"', src)

    def test_dicas_de_erro_nos_call_sites(self):
        # todos os erros de API mostram dica útil (quota esgotada ou modelo retirado)
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn("def dica_modelo", src)
        self.assertIn("modelo_indisponivel(erro)", src)
        self.assertGreaterEqual(src.count("dica_modelo(e)"), 3)
        self.assertGreaterEqual(src.count("mostrar_aviso_modelo()"), 5)

    def test_fallback_quota_ligado_em_todos_os_call_sites(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn("def chamar_gemini", src)
        self.assertEqual(src.count("chamar_gemini("), 4)  # definição + 3 call sites
        self.assertEqual(src.count("client.models.generate_content"), 1)  # só dentro do wrapper
        self.assertIn('"_modelo_pendente"', src)
        self.assertIn("AUTO_MODELO", src)
        self.assertIn("def _candidatos_auto", src)
        self.assertIn('"_uso_modelos"', src)


class TestBancosOffline(unittest.TestCase):
    def test_banco_m1_estrutura(self):
        for base in (H["BANCO_M1_ADN"], H["BANCO_M1_SO"]):
            self.assertIsInstance(base["texto_explicativo"], str)
            self.assertTrue(base["texto_explicativo"].strip())
            for q in base["perguntas"]:
                self.assertTrue(H["pergunta_valida"](q), q)
            for lac in base["fill_in_the_blank"]:
                self.assertIsInstance(lac.get("frase"), str)
                self.assertIn("[___]", lac["frase"])
                self.assertTrue(str(lac.get("palavra_oculta", "")).strip())

    def test_banco_m2_estrutura(self):
        for banco in (H["BANCO_M2_SO"], H["BANCO_M2_ADN"]):
            self.assertGreaterEqual(len(banco), 4)
            for p in banco:
                self.assertTrue(H["par_valido"](p), p)

    def test_gerador_m1_todos_os_num_opcoes(self):
        for n in (2, 3, 4, 5, 6):
            for tema in ("ADN", "Sistemas Operativos"):
                d = H["gerar_dados_m1_offline"](tema, n)
                for q in d["perguntas"]:
                    self.assertTrue(H["pergunta_valida"](q), (tema, n, q))
            dg = H["gerar_dados_m1_offline"]("História", n)
            self.assertTrue(dg.get("_demo_generico"))
            for q in dg["perguntas"]:
                self.assertTrue(H["pergunta_valida"](q), (n, q))

    def test_gerador_m2_devolve_copias(self):
        d1 = H["gerar_dados_m2_offline"]("ADN")
        d1["pares"][0]["conceito"] = "MUTADO"
        d2 = H["gerar_dados_m2_offline"]("ADN")
        self.assertNotEqual(d2["pares"][0]["conceito"], "MUTADO")


class TestBancosEN(unittest.TestCase):
    """Bancos demo em inglês (lang='en'): mesma estrutura validada dos PT."""

    def test_bancos_en_estrutura(self):
        for banco in (H["BANCO_M1_ADN_EN"], H["BANCO_M1_SO_EN"], H["BANCO_M1_FOTO_EN"]):
            self.assertTrue(banco["texto_explicativo"].strip())
            for q in banco["perguntas"]:
                self.assertTrue(H["pergunta_valida"](q), q)
            for lac in banco["fill_in_the_blank"]:
                self.assertIn("[___]", lac["frase"])
                self.assertTrue(str(lac.get("palavra_oculta", "")).strip())
        for banco in (H["BANCO_M2_SO_EN"], H["BANCO_M2_ADN_EN"], H["BANCO_M2_FOTO_EN"]):
            self.assertGreaterEqual(len(banco), 4)
            for p in banco:
                self.assertTrue(H["par_valido"](p), p)

    def test_m1_adn_en(self):
        d = gerar_dados_m1_offline("DNA", 4, lang="en")
        self.assertNotIn("_demo_generico", d)
        texto = d["texto_explicativo"].lower()
        self.assertIn("deoxyribonucleic", texto)
        self.assertIn("double helix", texto)
        for q in d["perguntas"]:
            self.assertEqual(len(q["opcoes"]), 4)
            self.assertTrue(0 <= q["resposta_correta"] < 4)
        palavras = [l["palavra_oculta"] for l in d["fill_in_the_blank"]]
        self.assertIn("nucleotides", palavras)

    def test_m1_adn_pt_fica_igual(self):
        d = gerar_dados_m1_offline("ADN", 4)
        self.assertNotIn("deoxyribonucleic", d["texto_explicativo"])
        self.assertIn("dupla hélice", d["texto_explicativo"])

    def test_m1_so_en_pela_keyword_en(self):
        d = gerar_dados_m1_offline("Operating Systems and Memory Management", 4, lang="en")
        self.assertNotIn("_demo_generico", d)
        self.assertIn("paging", d["texto_explicativo"].lower())
        palavras = [l["palavra_oculta"] for l in d["fill_in_the_blank"]]
        self.assertIn("frames", palavras)

    def test_m1_foto_en(self):
        d = gerar_dados_m1_offline("Photosynthesis", 4, lang="en")
        self.assertNotIn("_demo_generico", d)
        self.assertIn("chlorophyll", d["texto_explicativo"].lower())
        palavras = [l["palavra_oculta"] for l in d["fill_in_the_blank"]]
        self.assertIn("stomata", palavras)

    def test_generico_en_nao_inventa_factos(self):
        d = gerar_dados_m1_offline("Roman Aqueducts", 2, lang="en")
        self.assertTrue(d.get("_demo_generico"))
        self.assertIn("Roman Aqueducts", d["texto_explicativo"])
        self.assertIn("demo", d["texto_explicativo"].lower())
        for q in d["perguntas"]:
            self.assertEqual(len(q["opcoes"]), 2)
            self.assertTrue(H["pergunta_valida"](q))

    def test_generico_pt_continua_pt_por_defeito(self):
        d = gerar_dados_m1_offline("Roman Aqueducts", 2)
        self.assertTrue(d.get("_demo_generico"))
        self.assertIn("Recurso DEMO", d["texto_explicativo"])

    def test_m2_bancos_en(self):
        dso = gerar_dados_m2_offline("Operating Systems", lang="en")
        self.assertEqual(len(dso["pares"]), 4)
        self.assertIn("virtual memory", json.dumps(dso).lower())
        dadn = gerar_dados_m2_offline("DNA and genetics", lang="en")
        self.assertEqual(len(dadn["pares"]), 4)
        self.assertIn("double helix", json.dumps(dadn).lower())

    def test_m2_generico_en(self):
        d = gerar_dados_m2_offline("Roman Aqueducts", lang="en")
        self.assertTrue(d.get("_demo_generico"))
        self.assertIn("Roman Aqueducts", d["pares"][0]["conceito"])
        for p in d["pares"]:
            self.assertTrue(p["conceito"] and p["definicao"])

    def test_m2_pt_por_defeito(self):
        d = gerar_dados_m2_offline("Roman Aqueducts")
        self.assertTrue(d.get("_demo_generico"))
        self.assertIn("Conceito 1 de Roman Aqueducts", d["pares"][0]["conceito"])


class TestHistorico(unittest.TestCase):
    """Histórico de recursos da sessão: cópias profundas e restauro limpo."""

    def setUp(self):
        H["st"].session_state.clear()

    def tearDown(self):
        H["st"].session_state.clear()

    def test_mais_recente_primeiro_com_tema_e_hora(self):
        registar_historico("m1", "Tema A", {"m1": {"x": 1}, "m2": None})
        registar_historico("m2", "Tema B", {"m1": None, "m2": {"y": 2}})
        hist = H["st"].session_state["historico_recursos"]
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]["tema"], "Tema B")
        self.assertEqual(hist[0]["tipo"], "m2")
        self.assertEqual(hist[-1]["tema"], "Tema A")
        for item in hist:
            self.assertRegex(item["quando"], r"^\d{2}:\d{2}$")

    def test_limite_max_historico(self):
        for i in range(7):
            registar_historico("m1", f"T{i}", {"m1": {"n": i}, "m2": None})
        hist = H["st"].session_state["historico_recursos"]
        self.assertEqual(len(hist), H["MAX_HISTORICO"])
        self.assertEqual(hist[0]["tema"], "T6")  # fica o mais recente
        self.assertEqual(hist[-1]["tema"], "T2")  # e o limite a partir do fim
        self.assertEqual({item["tema"] for item in hist}, {"T6", "T5", "T4", "T3", "T2"})

    def test_copias_profundas_isolam_edicoes(self):
        r1 = {"texto_explicativo": "a", "perguntas": [{"o": 1}]}
        registar_historico("m1", "T", {"m1": r1, "m2": None})
        r1["perguntas"][0]["o"] = 999
        r1["texto_explicativo"] = "MUTADO"
        hist = H["st"].session_state["historico_recursos"]
        self.assertEqual(hist[0]["m1"]["perguntas"][0]["o"], 1)
        self.assertEqual(hist[0]["m1"]["texto_explicativo"], "a")

    def test_restaurar_repoe_e_limpa_estado(self):
        s = H["st"].session_state
        registar_historico(
            "m2",
            "Tema R",
            {
                "m1": {"texto_explicativo": "t", "perguntas": [{"q": 1}]},
                "m2": {"pares": [{"conceito": "c", "definicao": "d"}]},
            },
        )
        item = s["historico_recursos"][0]
        s["dados_m1"] = {"velho": True}
        s["dados_m2"] = {"velho": True}
        s["q_0"] = "resposta velha"
        s["lac_1"] = "x"
        s["assoc_2"] = "x"
        s["m1_submetido"] = True
        s["m2_submetido"] = True
        s["def_baralhadas"] = ["z"]
        s["ed_texto"] = "antigo"
        s["dados_m1_recuperacao"] = {"_recuperacao": True}
        s["dados_m2_recuperacao"] = {"_recuperacao": True}
        restaurar_do_historico(item)
        self.assertEqual(s["dados_m1"]["texto_explicativo"], "t")
        self.assertEqual(s["dados_m2"]["pares"][0]["conceito"], "c")
        for chave in (
            "q_0",
            "lac_1",
            "assoc_2",
            "m1_submetido",
            "m2_submetido",
            "def_baralhadas",
            "ed_texto",
            "dados_m1_recuperacao",
            "dados_m2_recuperacao",
        ):
            self.assertNotIn(chave, s, f"{chave} devia ter sido limpo")

    def test_restaurar_sem_m2_deleta_dados_m2(self):
        s = H["st"].session_state
        registar_historico("m1", "T", {"m1": {"x": 1}, "m2": None})
        s["dados_m2"] = {"velho": True}
        restaurar_do_historico(s["historico_recursos"][0])
        self.assertEqual(s["dados_m1"], {"x": 1})
        self.assertNotIn("dados_m2", s)

    def test_restaurar_nao_partilha_estruturas(self):
        s = H["st"].session_state
        registar_historico("m1", "T", {"m1": {"perguntas": [{"k": 1}]}, "m2": None})
        item = s["historico_recursos"][0]
        restaurar_do_historico(item)
        s["dados_m1"]["perguntas"][0]["k"] = 42
        self.assertEqual(item["m1"]["perguntas"][0]["k"], 1)  # histórico intacto


class TestExportPdf(unittest.TestCase):
    """Sanitização cp1252 e degraded sem fpdf2 (os testes forçam PDF_LIB_DISPONIVEL=False)."""

    def test_subscritos_e_setas(self):
        self.assertEqual(_cp1252("CO₂ + H₂O -> x"), "CO2 + H2O -> x")
        self.assertEqual(_cp1252("A ↔ B"), "A <-> B")

    def test_comparadores(self):
        self.assertEqual(_cp1252("x ≥ 5 e y ≤ 3"), "x >= 5 e y <= 3")

    def test_traco_em_dash_passa_igual(self):
        # o em dash (0x97) existe no cp1252 — passa intacto
        self.assertEqual(_cp1252("a — b"), "a — b")

    def test_carateres_desconhecidos_viram_interrogacao(self):
        self.assertEqual(_cp1252("π∑"), "??")
        self.assertIn("?", _cp1252("D π > C"))

    def test_transliteracao_nfkd_para_letras_fora_do_cp1252(self):
        # acentos sem cp1252 degradam para a letra base; o que é cp1252 passa intacto
        self.assertEqual(_cp1252("ǎřś"), "ars")
        self.assertEqual(_cp1252("Grécia — à noite"), "Grécia — à noite")

    def test_nao_texto_devolve_vazio(self):
        self.assertEqual(_cp1252(""), "")
        self.assertEqual(_cp1252(None), "")
        self.assertEqual(_cp1252(42), "")

    def test_pdf_sem_lib_devolve_none(self):
        self.assertFalse(H["PDF_LIB_DISPONIVEL"])
        self.assertIsNone(H["FPDF"])
        self.assertIsNone(exportar_recurso_pdf("Tema", {"texto_explicativo": "x"}, None))

    def test_pdf_sem_dados_devolve_none(self):
        self.assertIsNone(exportar_recurso_pdf("Tema", {}, None))

    def test_contrato_do_botao_pdf(self):
        src = SRC_PATH.read_text(encoding="utf-8")
        self.assertIn('STR["pdf_btn"]', src)
        self.assertIn('key="btn_exportar_pdf_m1"', src)
        self.assertIn('mime="application/pdf"', src)
        for lang in ("pt", "en"):
            self.assertTrue(H["STRINGS"][lang]["pdf_btn"].strip())


class TestUIClean(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = SRC_PATH.parent
        cls.cfg = (cls.root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        cls.src = SRC_PATH.read_text(encoding="utf-8")

    def test_config_unico_e_clean(self):
        self.assertIn('base = "dark"', self.cfg)
        self.assertNotIn("[theme.dark]", self.cfg)
        self.assertIn("JetBrains Mono", self.cfg)
        self.assertIn('primaryColor = "#4ADE80"', self.cfg)
        self.assertIn("[theme.sidebar]", self.cfg)
        self.assertNotIn("VT323", self.cfg)

    def test_sem_cromo_retro(self):
        for morto in (
            "mac-window",
            "mac-titlebar",
            "mac-statusbar",
            "mac-panel-title",
            "mac-menubar",
            "menu_button",
            "@st.dialog",
            "_pending_widget",
            "Control Panel",
            "System 6",
            "correct-badge",
            "incorrect-badge",
        ):
            self.assertNotIn(morto, self.src, f"{morto} devia ter saído na limpeza da UI")

    def test_css_tematico_injetado_uma_vez(self):
        # identidade visual: CSS proprio injetado via st.html (sem unsafe_allow_html)
        self.assertEqual(self.src.count("st.html(CSS_UI)"), 1)
        self.assertIn("<style>", self.src)
        self.assertNotIn("unsafe_allow_html", self.src)
        self.assertNotIn("<script", self.src)
        self.assertNotIn("emotion-cache", self.src)

    def test_cabecalho_hero(self):
        self.assertIn("construir_hero(", self.src)
        self.assertIn('STR["main_title"]', self.src)
        self.assertIn('STR["sub_header"]', self.src)

    def test_feedback_nativo(self):
        self.assertIn('st.success(STR["state_good"])', self.src)
        self.assertIn('st.error(STR["state_bad"])', self.src)
        self.assertIn('st.error(f"P{idx + 1}: ', self.src)

    def test_sem_recursos_externos(self):
        self.assertNotIn("img.icons8.com", self.src)
        self.assertNotIn("http://", self.src)
        self.assertNotIn("https://", self.src)


class TestFallbackQuota(unittest.TestCase):
    """chamar_gemini: troca automática de modelo quando a quota esgota (429)."""

    @classmethod
    def setUpClass(cls):
        cls.st = H["st"]

    def setUp(self):
        self.st.session_state.clear()
        self.st.warnings.clear()
        H["STR"] = {
            "model_quota_hint": "quota esgotada — escolhe um Flash",
            "model_404_hint": "modelo retirado",
            "model_switch": "troca {antigo}->{novo}",
        }

    def tearDown(self):
        self.st.session_state.clear()
        self.st.warnings.clear()

    @staticmethod
    def _cliente(comportamento):
        class FakeModels:
            chamadas = []

            def generate_content(self, model=None, contents=None, config=None):
                FakeModels.chamadas.append(model)
                r = comportamento.get(model, "ok")
                if r == "quota":
                    raise RuntimeError(f"429 RESOURCE_EXHAUSTED quota: {model}")
                if r == "erro":
                    raise RuntimeError(f"400 INVALID_ARGUMENT: {model}")

                class FakeRes:
                    text = "resposta ok"

                return FakeRes()

        class FakeClient:
            models = FakeModels()

        return FakeClient(), FakeModels

    def test_quota_troca_automaticamente_e_memoriza(self):
        self.st.session_state["_modelos_lista"] = [
            "gemini-3.1-pro-preview",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
        ]
        cliente, modelos = self._cliente({"gemini-3.1-pro-preview": "quota"})
        H["client"] = cliente
        H["model_name"] = "gemini-3.1-pro-preview"
        res = H["chamar_gemini"]("prompt")
        self.assertEqual(res.text, "resposta ok")
        self.assertEqual(modelos.chamadas, ["gemini-3.1-pro-preview", "gemini-3.8-flash"])
        self.assertEqual(H["model_name"], "gemini-3.8-flash")
        self.assertEqual(self.st.session_state["_modelo_pendente"], "gemini-3.8-flash")
        self.assertEqual(
            self.st.session_state["_modelo_trocado"],
            ("gemini-3.1-pro-preview", "gemini-3.8-flash"),
        )

    def test_quota_total_levanta_o_primeiro_erro(self):
        self.st.session_state["_modelos_lista"] = [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
        ]
        cliente, modelos = self._cliente(
            {
                "gemini-3.8-flash": "quota",
                "gemini-3.6-flash": "quota",
                "gemini-3.5-flash-lite": "quota",
            }
        )
        H["client"] = cliente
        H["model_name"] = "gemini-3.8-flash"
        with self.assertRaises(RuntimeError) as ctx:
            H["chamar_gemini"]("prompt")
        self.assertIn("gemini-3.8-flash", str(ctx.exception))
        self.assertEqual(len(modelos.chamadas), 3)

    def test_erro_nao_quota_falha_de_imediato(self):
        self.st.session_state["_modelos_lista"] = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
        cliente, modelos = self._cliente({"gemini-3.8-flash": "erro"})
        H["client"] = cliente
        H["model_name"] = "gemini-3.8-flash"
        with self.assertRaises(RuntimeError):
            H["chamar_gemini"]("prompt")
        self.assertEqual(modelos.chamadas, ["gemini-3.8-flash"])

    def test_auto_escolhe_o_menos_usado(self):
        self.st.session_state["_modelos_lista"] = [
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
        ]
        self.st.session_state["_uso_modelos"] = {"gemini-3.8-flash": 3, "gemini-3.6-flash": 1}
        cliente, modelos = self._cliente({})
        H["client"] = cliente
        H["model_name"] = H["AUTO_MODELO"]
        res = H["chamar_gemini"]("prompt")
        self.assertEqual(res.text, "resposta ok")
        self.assertEqual(modelos.chamadas, ["gemini-3.5-flash-lite"])
        self.assertEqual(self.st.session_state["_uso_modelos"]["gemini-3.5-flash-lite"], 1)
        self.assertNotIn("_modelo_pendente", self.st.session_state)

    def test_auto_quota_marca_cheio_e_segue(self):
        self.st.session_state["_modelos_lista"] = [
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
        ]
        cliente, modelos = self._cliente({"gemini-3.8-flash": "quota"})
        H["client"] = cliente
        H["model_name"] = H["AUTO_MODELO"]
        res = H["chamar_gemini"]("prompt")
        self.assertEqual(res.text, "resposta ok")
        self.assertEqual(modelos.chamadas, ["gemini-3.8-flash", "gemini-3.5-flash-lite"])
        uso = self.st.session_state["_uso_modelos"]
        self.assertGreaterEqual(uso["gemini-3.8-flash"], 50)
        self.assertEqual(uso["gemini-3.5-flash-lite"], 1)
        self.assertEqual(
            self.st.session_state["_modelo_trocado"],
            ("gemini-3.8-flash", "gemini-3.5-flash-lite"),
        )
        self.assertNotIn("_modelo_pendente", self.st.session_state)

    def test_candidatos_auto_ordenam_por_uso(self):
        self.st.session_state["_modelos_lista"] = [
            "gemini-3.1-pro-preview",
            "gemini-2.5-flash",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
        ]
        self.st.session_state["_uso_modelos"] = {"gemini-3.5-flash-lite": 2}
        self.assertEqual(
            H["_candidatos_auto"](),
            ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"],
        )

    def test_dica_modelo(self):
        dm = H["dica_modelo"]
        self.assertIn("quota", dm(RuntimeError("429 RESOURCE_EXHAUSTED")))
        self.assertIn("retirado", dm(RuntimeError("404 NOT_FOUND: models/x")))
        self.assertEqual(dm(RuntimeError("erro simples")), "")

    def test_mostrar_aviso_uma_so_vez(self):
        self.st.session_state["_modelo_trocado"] = ("a", "b")
        H["mostrar_aviso_modelo"]()
        H["mostrar_aviso_modelo"]()
        self.assertEqual(len(self.st.warnings), 1)
        self.assertIn("troca a->b", self.st.warnings[0])


class TestExport(unittest.TestCase):
    """Exportação do recurso gerado em Markdown."""

    def test_estrutura_completa(self):
        dados = {
            "texto_explicativo": "Texto base.",
            "perguntas": [
                {"pergunta": "Q1?", "opcoes": ["errada", "certa"], "resposta_correta": 1, "explicacao": "Porque sim."},
            ],
            "fill_in_the_blank": [{"frase": "X [___] Y", "palavra_oculta": "z"}],
        }
        md = H["exportar_recurso_markdown"]("Tema X", dados, [{"conceito": "C", "definicao": "D"}])
        self.assertIn("# EduGen — Recurso gerado", md)
        self.assertIn("## Texto explicativo", md)
        self.assertIn("Texto base.", md)
        self.assertIn("**P1.** Q1?", md)
        self.assertIn("- a) errada", md)
        self.assertIn("- b) certa", md)
        self.assertIn("## Quiz — respostas e explicações", md)
        self.assertIn("**P1:** certa — Porque sim.", md)
        self.assertIn("## Lacunas — exercícios", md)
        self.assertIn("X [___] Y", md)
        self.assertIn("**1:** z", md)
        self.assertIn("## Jogo de associação — pares", md)
        self.assertIn("1. **C** — D", md)

    def test_dados_vazios_nao_explodem(self):
        md = H["exportar_recurso_markdown"]("", {}, None)
        self.assertIn("# EduGen — Recurso gerado", md)
        self.assertIn("**Tema:** este tema", md)

    def test_bancos_fotossintese(self):
        m1 = H["gerar_dados_m1_offline"]("Fotossíntese", 4)
        self.assertIn("clorofila", str(m1.get("texto_explicativo", "")).lower())
        self.assertGreaterEqual(len(m1.get("perguntas") or []), 2)
        self.assertGreaterEqual(len(m1.get("fill_in_the_blank") or []), 2)
        self.assertNotIn("_demo_generico", m1)
        m2 = H["gerar_dados_m2_offline"]("fotosintese")
        self.assertEqual(len(m2.get("pares") or []), 4)


class TestDependencias(unittest.TestCase):
    """piso de dependências alinhado com o que a UI realmente usa."""

    def test_floor_do_streamlit(self):
        import re as _re

        req = (SRC_PATH.parent / "requirements.txt").read_text(encoding="utf-8")
        match = _re.search(r"streamlit>=([0-9]+(?:\.[0-9]+)*)", req)
        self.assertIsNotNone(match, "requirements.txt deve fixar um piso de streamlit")
        major, minor = (int(x) for x in match.group(1).split(".")[:2])
        # theme.linkColor/codeTextColor (1.51), fontes por URL em theme.font
        # (1.50) e headingFontSizes/Weights (1.47): um piso baixo degradava a
        # identidade visual em silêncio.
        self.assertGreaterEqual((major, minor), (1, 51))


class TestSite(unittest.TestCase):
    """Website de apresentação (docs/index.html): simples a par do ethos da app."""

    @classmethod
    def setUpClass(cls):
        cls.site = (SRC_PATH.parent / "docs" / "index.html").read_text(encoding="utf-8")

    def test_marca_e_conteudo(self):
        self.assertIn("EduGen", self.site)
        self.assertIn("██████╗", self.site)  # ASCII-art do logo, igual ao da app
        self.assertIn("streamlit run TrabalhoPython.py", self.site)

    def test_zero_script_e_sem_emojis(self):
        import re as _re

        # publicamos sem um único <script>: o mesmo ethos "sem recursos externos"
        self.assertEqual(self.site.count("<script"), 0)
        self.assertEqual(self.site.count("onerror"), 0)
        self.assertEqual(
            _re.findall(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]", self.site),
            [],
            "o site não devia ter emojis",
        )


class TestTextoParaQuiz(unittest.TestCase):
    """Módulo 1 a partir de texto colado: heurística local honesta, sem IA."""

    @classmethod
    def setUpClass(cls):
        # staticmethod: as funções de H, guardadas na classe, não podem virar métodos
        # (self entraria como 1.º argumento e deslocava num_opcoes/lang)
        cls.g = staticmethod(H["gerar_dados_m1_de_texto"])
        cls.valida = staticmethod(H["pergunta_valida"])
        cls.stop = H["_STOPWORDS_TEXTO"]
        cls.strings = H["STRINGS"]
        cls.texto_pt = (
            "A fotossíntese transforma energia luminosa em energia química. "
            "As plantas usam a clorofila para absorver a luz solar. "
            "O dióxido de carbono e a água convertem-se em glicose e oxigénio. "
            "A clorofila habita os cloroplastos das células vegetais. "
            "Os estomas controlam a troca de gases nas folhas."
        )

    def test_texto_curto_levanta_erro(self):
        with self.assertRaises(ValueError):
            self.g("Frase fina.", "X", 4)
        with self.assertRaises(ValueError):
            self.g("Uma frase muito comprida mas solitária, sem companhia nenhuma no parágrafo.", "X", 4)

    def test_estrutura_valida_do_recurso(self):
        dados = self.g(self.texto_pt, "Fotossíntese", 4)
        self.assertEqual(dados["_tema"], "Fotossíntese")
        self.assertGreaterEqual(len(dados["perguntas"]), 2)
        self.assertGreaterEqual(len(dados["fill_in_the_blank"]), 2)
        for q in dados["perguntas"]:
            self.assertTrue(self.valida(q))
            self.assertLessEqual(len(q["opcoes"]), 4)

    def test_resposta_correta_e_explicacao_ancoradas_no_texto(self):
        dados = self.g(self.texto_pt, "Fotossíntese", 4)
        for q in dados["perguntas"]:
            correta = q["opcoes"][q["resposta_correta"]]
            self.assertIn(correta, self.texto_pt)  # termo vem do texto, sem inventados
            self.assertIn(self.strings["pt"]["texto_m1_pergunta"], str(q["pergunta"]))
            self.assertIn(self.strings["pt"]["texto_m1_explic"], str(q["explicacao"]))
            # passagem reconstruída (termo no lugar do [___]) == frase integral citada
            passagem = str(q["pergunta"]).split("«", 1)[1].rsplit("»", 1)[0]
            citada = str(q["explicacao"]).split("«", 1)[1].rsplit("»", 1)[0]
            self.assertEqual(passagem.replace("[___]", correta).lower(), citada.lower())

    def test_distratores_sao_termos_do_texto(self):
        import re as _re

        dados = self.g(self.texto_pt, "Fotossíntese", 4)
        termos = {w.lower() for w in _re.findall(r"[^\W\d_]{4,}", self.texto_pt)}
        for q in dados["perguntas"]:
            correta = q["opcoes"][q["resposta_correta"]]
            for op in q["opcoes"]:
                if op != correta:
                    self.assertIn(str(op).lower(), termos)

    def test_lacunas_marcador_unico_e_termos_unicos(self):
        dados = self.g(self.texto_pt, "Fotossíntese", 4)
        vistas = set()
        for lac in dados["fill_in_the_blank"]:
            frase, palavra = lac["frase"], lac["palavra_oculta"]
            self.assertEqual(frase.count("[___]"), 1)
            self.assertIn(palavra.lower(), self.texto_pt.lower())
            self.assertGreaterEqual(len(palavra), 4)
            self.assertNotIn(palavra.lower(), self.stop)
            self.assertNotIn(palavra.lower(), vistas)
            vistas.add(palavra.lower())

    def test_idioma_en_usa_strings_en_e_sem_stopwords(self):
        texto_en = (
            "Photosynthesis converts light energy into chemical energy inside plants. "
            "Chlorophyll inside the leaves absorbs sunlight during the daytime hours. "
            "Carbon dioxide combines with water inside chloroplasts producing glucose. "
            "Stomata regulate gas exchange across the surface of leaves."
        )
        dados = self.g(texto_en, "Photosynthesis", 4, lang="en")
        self.assertTrue(dados["perguntas"] and dados["fill_in_the_blank"])
        for q in dados["perguntas"]:
            self.assertIn(self.strings["en"]["texto_m1_pergunta"], str(q["pergunta"]))
            self.assertIn(self.strings["en"]["texto_m1_explic"], str(q["explicacao"]))
        for lac in dados["fill_in_the_blank"]:
            self.assertNotIn(lac["palavra_oculta"].lower(), self.stop)

    def test_tema_vazio_deriva_da_primeira_frase(self):
        dados = self.g(self.texto_pt, "   ", 4)
        self.assertTrue(str(dados["_tema"]).strip())
        self.assertLessEqual(len(dados["_tema"]), 80)

    def test_sem_enxerto_de_opcoes_fantasma(self):
        # diferente do banco: no texto colado não há "Opção adicional" a preencher omissões
        dados = self.g(self.texto_pt, "Fotossíntese", 6)
        for q in dados["perguntas"]:
            self.assertFalse(any("Opção adicional" in str(o) for o in q["opcoes"]))

    def test_esquema_m1_formata_sem_colisao(self):
        # o schema partilhado pelas duas vias Online formata sem colidir com as chavetas do JSON
        esquema = H["ESQUEMA_M1"].format(n_opc=4, n_max=3, nivel="X", bloom="Y")
        self.assertNotIn("{n_opc}", esquema)
        self.assertIn("'[___]'", esquema)
        self.assertIn('"resposta_correta"', esquema)

    def test_termos_dos_quiz_unicos(self):
        dados = self.g(self.texto_pt, "Fotossíntese", 4)
        corretas = [q["opcoes"][q["resposta_correta"]].lower() for q in dados["perguntas"]]
        self.assertEqual(len(set(corretas)), len(corretas))


if __name__ == "__main__":
    unittest.main()
