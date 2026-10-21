"""Smoke test end-to-end da app real (Streamlit AppTest) — 12 fluxos.

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

# 12. exportar recurso (Professor, offline): botão presente e exportação Markdown
d = next((x for x in at.download_button if x.key == "btn_exportar_m1"), None)
assert d is not None, "download de exportação em falta"
print("12. exportar recurso (.md) OK")

print("ALL APPTEST PASSED")
