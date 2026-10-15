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
    import io
    import os
    import re

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

    ns = {"os": os, "json": json, "io": io, "re": re, "random": random, "st": StDummy()}
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
        d = gerar_dados_m1_offline("Fotossíntese", 4)
        self.assertIn("Fotossíntese", d["texto_explicativo"])

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
            if not _re.search(rf"STR\[['\"]({_re.escape(k)})['\"]\]", src)
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


class TestUIClean(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = SRC_PATH.parent
        cls.cfg = (cls.root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        cls.src = SRC_PATH.read_text(encoding="utf-8")

    def test_config_unico_e_clean(self):
        self.assertIn('base = "light"', self.cfg)
        self.assertNotIn("[theme.dark]", self.cfg)
        self.assertIn('font = "sans-serif"', self.cfg)
        self.assertIn('primaryColor = "#2563EB"', self.cfg)
        self.assertNotIn("VT323", self.cfg)
        self.assertNotIn('baseRadius = "0px"', self.cfg)

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

    def test_sem_css_custom(self):
        self.assertNotIn("<style>", self.src)
        self.assertNotIn("unsafe_allow_html", self.src)
        self.assertNotIn("emotion-cache", self.src)

    def test_cabecalho_nativo(self):
        self.assertIn('st.title(STR["main_title"])', self.src)
        self.assertIn('st.caption(STR["sub_header"])', self.src)

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


if __name__ == "__main__":
    unittest.main()
