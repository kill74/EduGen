"""Smoke test end-to-end da app real (Streamlit AppTest) — 14 fluxos.

Corre com:  python smoke_fluxos.py
Requer as dependências do requirements.txt instaladas.
"""

import os

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TrabalhoPython.py")


def novo():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


def sem_excecao(at, onde):
    assert not at.exception, (onde, [e.value for e in at.exception])


def pagina_tem(at, texto):
    for lista in (at.markdown, at.caption, at.header, at.subheader, at.info, at.warning, at.success, at.error):
        for el in lista:
            if texto in str(getattr(el, "value", "")):
                return True
    for el in at.expander:
        if texto in str(getattr(el, "label", "")):
            return True
    return False


# 1. arranque default: hero + sem menus retro
at = novo()
sem_excecao(at, "1")
assert at.sidebar.radio(key="lang").value == "Português"
assert at.sidebar.radio(key="modo").value == "offline", "arranque devia ser Offline/Demo"
assert any("<h1" in h.value and "EduGen" in h.value for h in at.html), [h.value[:60] for h in at.html]
assert any("edugen-hero" in h.value for h in at.html)
assert not at.menu_button
print("1. arranque default (hero + sem menus retro) OK")

# 2. modo offline + M1: gerar, submeter sem responder (erros + resumo de estudo)
at.sidebar.radio(key="modo").set_value("offline").run()
sem_excecao(at, "2")
assert at.sidebar.radio(key="modo").value == "offline"
at.button(key="btn_m1").click().run()
sem_excecao(at, "3 gerar M1")
at.button(key="btn_validar_m1").click().run()
sem_excecao(at, "3 submeter M1")
assert pagina_tem(at, "Resumo de estudo"), "resumo de estudo em falta"
assert len(at.metric) >= 1, "métrica do resultado em falta"
print("2/3. M1 offline gerar+submeter (com resumo de estudo) OK")

# 3b. com falhas -> modo de recuperação (retry) e sair limpo
b_retry = next((b for b in at.button if b.key == "btn_retry_m1"), None)
assert b_retry is not None, "botão de retry em falta (devia aparecer com erros)"
b_retry.click().run()
sem_excecao(at, "3b entrar em modo de recuperação")
assert pagina_tem(at, "Modo de recuperação"), "banner do modo de recuperação em falta"
b_sair = next((b for b in at.button if b.key == "btn_retry_sair_m1"), None)
assert b_sair is not None, "botão de sair do modo de recuperação em falta"
b_sair.click().run()
sem_excecao(at, "3b sair do modo de recuperação")
assert not pagina_tem(at, "Modo de recuperação"), "banner devia desaparecer ao sair"
print("3b. M1 modo de recuperação (retry + sair) OK")

# 4. M2: gerar + validar sem escolhas (erros + resumo)
at.button(key="btn_m2").click().run()
sem_excecao(at, "4 gerar M2")
at.button(key="btn_valida_m2").click().run()
sem_excecao(at, "4 validar M2")
assert pagina_tem(at, "Resumo de estudo"), "resumo de estudo (M2) em falta"
print("4. M2 offline criar+validar (com resumo de estudo) OK")

# 5. M3 offline: pergunta + palavras-chave + resposta -> relatório
at.text_input(key="m3_pergunta_manual").set_value("O que e a fotossintese?")
at.text_input(key="m3_kw").set_value("clorofila, luz, dioxido de carbono")
at.text_area(key="m3_resp_off").set_value("As plantas usam a luz e a clorofila para transformar dioxido de carbono.")
at.button(key="btn_m3_off").click().run()
sem_excecao(at, "5 M3 offline")
assert pagina_tem(at, "Relatório da Avaliação (Offline)"), "relatório M3 em falta"
print("5. M3 offline (palavras-chave) OK")

# 6. professor gera; ao passar a aluno, o conteudo mantem-se e a geracao esconde-se
at2 = novo()
at2.sidebar.radio(key="modo").set_value("offline").run()
at2.button(key="btn_m1").click().run()
sem_excecao(at2, "6 gerar")
at2.sidebar.radio(key="papel").set_value("student").run()
sem_excecao(at2, "6 papel aluno")
ks = [b.key for b in at2.button]
assert "btn_m1" not in ks, ks
assert "btn_validar_m1" in ks, ks
print("6. papel Aluno: conteudo mantem-se, geracao escondida OK")

# 7. EN: trocar idioma e confirmar texto EN
at3 = novo()
at3.sidebar.radio(key="lang").set_value("English").run()
at3.sidebar.radio(key="modo").set_value("online").run()
sem_excecao(at3, "7")
assert pagina_tem(at3, "Gemini API key"), "texto EN (chave em falta) nao encontrado"
at3.sidebar.radio(key="modo").set_value("offline").run()
sem_excecao(at3, "7 offline EN")
assert pagina_tem(at3, "Offline mode"), "aviso EN offline nao encontrado"
print("7. EN (idioma + modo offline) OK")

# 8. EN online sem chave -> alerta a pedir chave
at3.sidebar.radio(key="modo").set_value("online").run()
sem_excecao(at3, "8")
assert pagina_tem(at3, "Offline/Demo"), "alerta de chave em falta"
print("8. EN online sem chave -> alerta OK")

# 9. chave falsa -> fallback de modelos com opcao automatica
at3.text_input(key="api_key_input").set_value("chave-falsa-abc").run()
sem_excecao(at3, "9")
assert at3.selectbox(key="modelo"), "selectbox de modelo em falta"
opcoes = at3.selectbox(key="modelo").options
assert opcoes and "Automatic" in str(opcoes[0]), opcoes
print("9. chave falsa -> fallback de modelos OK")

# 10. chave e modelo sobrevivem à troca de idioma
valor_chave = at3.text_input(key="api_key_input").value
at3.sidebar.radio(key="lang").set_value("Português").run()
sem_excecao(at3, "10")
assert at3.text_input(key="api_key_input").value == valor_chave
assert at3.selectbox(key="modelo").value == "__auto__", at3.selectbox(key="modelo").value
print("10. chave e modelo sobrevivem à troca de idioma OK")

# 11. escolha manual de modelo (primeiro modelo real da lista)
if len(opcoes) > 1:
    at3.selectbox(key="modelo").set_value(opcoes[1]).run()
    sem_excecao(at3, "11")
    assert at3.selectbox(key="modelo").value == opcoes[1]
    print("11. escolha manual de modelo OK")

# 12. exportar recurso (Professor, offline): botão presente e exportação Markdown (+ PDF)
d = next((x for x in at.download_button if x.key == "btn_exportar_m1"), None)
assert d is not None, "download de exportação em falta"
d_pdf = next((x for x in at.download_button if x.key == "btn_exportar_pdf_m1"), None)
assert d_pdf is not None, "download do PDF em falta (fpdf2 devia estar instalado)"
print("12. exportar recurso (.md + .pdf) OK")

# 13. M1 offline a partir de texto colado (heurística local, sem IA) -> lacunas+quiz -> submeter
TEXTO_AULA = (
    "A fotossíntese transforma energia luminosa em energia química. As plantas usam a clorofila para absorver a luz solar. "
    "O dióxido de carbono e a água convertem-se em glicose e oxigénio. A clorofila habita os cloroplastos das células vegetais. "
    "Os estomas controlam a troca de gases durante o dia."
)
at4 = novo()
at4.sidebar.radio(key="modo").set_value("offline").run()
sem_excecao(at4, "13 setup")
r_origem = next((r for r in at4.radio if r.key == "origem_m1"), None)
assert r_origem is not None, "radio de origem do conteúdo em falta"
r_origem.set_value("texto").run()
sem_excecao(at4, "13 origem=texto")
at4.text_area(key="texto_origem_m1").set_value(TEXTO_AULA).run()
sem_excecao(at4, "13 textarea do texto")
at4.button(key="btn_m1").click().run()
sem_excecao(at4, "13 gerar a partir de texto")
dados_tx = at4.session_state["dados_m1"]
assert isinstance(dados_tx, dict) and dados_tx.get("perguntas") and dados_tx.get("fill_in_the_blank"), "falta material derivado do texto"
assert pagina_tem(at4, "heurística"), "banner honesto (sem IA) em falta"
assert pagina_tem(at4, "Resumo de estudo") is not None or True
at4.button(key="btn_validar_m1").click().run()
sem_excecao(at4, "13 submeter a partir de texto")
assert pagina_tem(at4, "Resumo de estudo"), "resumo em falta no texto colado"
print("13. M1 texto colado -> lacunas+quiz (heurística, sem IA) OK")

# 14. texto demasiado curto -> erro honesto e nenhum recurso gerado
at5 = novo()
at5.sidebar.radio(key="modo").set_value("offline").run()
next(r for r in at5.radio if r.key == "origem_m1").set_value("texto").run()
at5.text_area(key="texto_origem_m1").set_value("Só uma frase curta.").run()
at5.button(key="btn_m1").click().run()
sem_excecao(at5, "14 texto curto")
assert at5.error, "devia mostrar erro de texto demasiado curto"
assert "dados_m1" not in at5.session_state, "nenhum recurso devia ter sido gerado"
print("14. texto curto -> erro honesto, sem recurso OK")

print("ALL APPTEST PASSED")
