import io
import json
import os
import random
import re

import streamlit as st
from PIL import Image

# O import do Gemini é opcional: permite correr a app em modo Offline sem a lib instalada
try:
    from google import genai
    from google.genai import types

    GEMINI_LIB_DISPONIVEL = True
except ImportError:
    genai = None
    types = None
    GEMINI_LIB_DISPONIVEL = False


# ==========================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILIZAÇÃO DSI (UX/UI)
# ==========================================================
st.set_page_config(
    page_title="EduGen - Sistema Interativo de IA Generativa",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    /* ============ EduGen OS: retro System 6 chrome (own classes only) ============ */
    .st-key-menu_brand button,
    .st-key-menu_file button,
    .st-key-menu_edit button,
    .st-key-menu_view button,
    .st-key-menu_special button {
        font-size: 1.35rem;
    }
    .mac-window {
        background: #FFFFFF;
        border: 2px solid #111111;
        box-shadow: 5px 5px 0 #111111;
        margin-bottom: 1.2rem;
    }
    .mac-titlebar {
        height: 30px;
        background: repeating-linear-gradient(
            to bottom,
            #111111 0px, #111111 2px,
            #FFFFFF 2px, #FFFFFF 5px
        );
        border-bottom: 2px solid #111111;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .mac-title {
        background: #FFFFFF;
        border: 2px solid #111111;
        padding: 0 14px;
        font-size: 1.4rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .mac-body {
        padding: 1rem 1.2rem;
    }
    .mac-body .main-header {
        font-size: 1.9rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .mac-body .sub-header {
        font-size: 1.25rem;
    }
    .mac-statusbar {
        display: flex;
        justify-content: space-between;
        background: #FFFFFF;
        border-top: 3px solid #111111;
        padding: 0.3rem 1rem;
        font-size: 1.15rem;
        margin-top: 2rem;
    }
    .mac-statusbar .cursor {
        display: inline-block;
        width: 0.6em;
        height: 1.1em;
        background: #111111;
        vertical-align: text-bottom;
        animation: mac-blink 1.1s steps(1) infinite;
    }
    @keyframes mac-blink {
        50% { opacity: 0; }
    }
    .mac-panel-title {
        background: repeating-linear-gradient(
            to bottom,
            #111111 0px, #111111 2px,
            #FFFFFF 2px, #FFFFFF 5px
        );
        border: 2px solid #111111;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 0.8rem;
    }
    .mac-panel-title span {
        background: #FFFFFF;
        border-left: 2px solid #111111;
        border-right: 2px solid #111111;
        padding: 0 12px;
        font-size: 1.3rem;
        font-weight: 700;
    }
    .correct-badge {
        background: #111111;
        color: #FFFFFF;
        border: 2px solid #111111;
        box-shadow: 3px 3px 0 #888888;
        padding: 0.5rem 1rem;
        font-weight: 700;
        font-size: 1.2rem;
    }
    .correct-badge::before {
        content: "\\2713  ";
    }
    .incorrect-badge {
        background: #FFFFFF;
        color: #111111;
        border: 2px solid #111111;
        box-shadow: 3px 3px 0 #888888;
        padding: 0.5rem 1rem;
        font-weight: 700;
        font-size: 1.2rem;
    }
    .incorrect-badge::before {
        content: "\\2717  ";
    }
    /* Beveled 1-bit buttons + square inputs (stable widget hooks only) */
    div[data-testid="stButton"] button,
    div[data-testid="stBaseButton-primary"] button,
    div[data-testid="stBaseButton-secondary"] button {
        background: #FFFFFF;
        color: #111111;
        border: 2px solid #111111;
        border-radius: 0;
        box-shadow: 3px 3px 0 #111111;
        font-size: 1.2rem;
    }
    div[data-testid="stButton"] button:active,
    div[data-testid="stBaseButton-primary"] button:active,
    div[data-testid="stBaseButton-secondary"] button:active {
        transform: translate(2px, 2px);
        box-shadow: 1px 1px 0 #111111;
    }
    div[data-testid="stBaseButton-primary"] button {
        background: #111111;
        color: #FFFFFF;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextArea"] textarea {
        border: 2px solid #111111;
        border-radius: 0;
        background: #FFFFFF;
    }
    div[data-testid="stSelectbox"] > div {
        border: 2px solid #111111;
        border-radius: 0;
        background: #FFFFFF;
    }
    div[data-testid="stExpander"] {
        border: 2px solid #111111;
        border-radius: 0;
        background: #FFFFFF;
    }
    hr {
        border: none;
        border-top: 2px solid #111111;
        margin: 1rem 0;
    }
    input[type="radio"], input[type="checkbox"] {
        accent-color: #111111;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Aplica trocas de idioma/papel/modo pedidas via menu bar.
# Corre antes de qualquer widget: definir estes valores aqui é seguro.
if "_pending_widget" in st.session_state:
    _pk, _pv = st.session_state.pop("_pending_widget")
    st.session_state[_pk] = _pv


# ==========================================================
# FUNÇÕES AUXILIARES (robustez + modo offline)
# ==========================================================
def extrair_json_seguro(texto: str):
    """Faz parse de JSON vindo do LLM, mesmo com fences ```json ... ``` ou texto extra."""
    if not texto or not texto.strip():
        raise ValueError("Resposta vazia do modelo.")
    t = texto.strip()
    # Remove fences de markdown
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # Tenta extrair o maior bloco {...} válido
        ini = t.find("{")
        fim = t.rfind("}")
        if ini != -1 and fim != -1 and fim > ini:
            return json.loads(t[ini : fim + 1])
        raise


def normalizar(texto: str) -> str:
    """Normaliza respostas curtas para comparação (minúsculas, sem espaços/pontuação extra)."""
    t = str(texto or "").strip().lower()
    t = re.sub(r"[.\s;:!?,'\"()]+$", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def parse_nota_percentual(valor) -> int:
    """Converte a nota vinda da IA (int, float, '85', '85%') em int 0-100."""
    try:
        nota = int(float(str(valor).strip().rstrip("%")))
    except (ValueError, TypeError, AttributeError):
        return 0
    return max(0, min(100, nota))


def imagem_para_bytes(imagem) -> bytes:
    """Serializa uma PIL.Image em PNG para envio à API multimodal."""
    buf = io.BytesIO()
    imagem.save(buf, format="PNG")
    return buf.getvalue()


def limpar_respostas_antigas(prefixos=("q_", "lac_", "assoc_"), extras=()):
    """Remove respostas anteriores do session_state ao gerar novo recurso.

    O âmbito é limitado ao módulo gerado: gerar o M1 não apaga o jogo do M2
    nem a pergunta multimodal do M3 (evita perda de dados entre abas).
    """
    for k in list(st.session_state.keys()):
        if k.startswith(prefixos) or k in extras:
            del st.session_state[k]


def limpar_chaves_resposta_m1():
    """Limpa só as respostas do Módulo 1 (usado pelo editor incremental)."""
    for k in [k for k in st.session_state.keys() if k.startswith(("q_", "lac_"))]:
        del st.session_state[k]


def _eh_opcao(o) -> bool:
    """Uma opção tem de ser escalar (str/int/float); dicts/listas crashavam o st.radio."""
    return isinstance(o, (str, int, float)) and not isinstance(o, bool)


def pergunta_valida(q) -> bool:
    """Valida uma pergunta de escolha múltipla (online ou offline)."""
    if not isinstance(q, dict):
        return False
    opcoes = q.get("opcoes", [])
    idx = q.get("resposta_correta")
    return (
        isinstance(opcoes, list)
        and len(opcoes) > 0
        and all(_eh_opcao(o) for o in opcoes)
        and isinstance(idx, int)
        and not isinstance(idx, bool)
        and 0 <= idx < len(opcoes)
    )


def par_valido(p) -> bool:
    """Valida um par conceito-definição do jogo de associação."""
    if not isinstance(p, dict):
        return False
    for k in ("conceito", "definicao"):
        v = p.get(k)
        if not _eh_opcao(v) or str(v).strip() == "":
            return False
    return True


def ajustar_num_opcoes(pergunta: dict, num_opcoes: int) -> dict:
    """Adapta uma pergunta do banco offline para o nº de opções pedido (2-6)."""
    opcoes = list(pergunta.get("opcoes", []))
    idx_correta = pergunta.get("resposta_correta", 0)
    if (
        not opcoes
        or not isinstance(idx_correta, int)
        or isinstance(idx_correta, bool)
        or not (0 <= idx_correta < len(opcoes))
    ):
        return pergunta
    correta = opcoes[idx_correta]
    erradas = [o for i, o in enumerate(opcoes) if i != idx_correta]
    if num_opcoes <= 1:
        num_opcoes = 2
    # Mantém a correta + (num_opcoes-1) erradas; completa se faltarem
    escolhidas = [correta] + erradas[: max(0, num_opcoes - 1)]
    while len(escolhidas) < num_opcoes:
        escolhidas.append(f"Opção adicional {len(escolhidas) + 1}")
    random.shuffle(escolhidas)
    return {
        "pergunta": pergunta.get("pergunta", ""),
        "opcoes": escolhidas,
        "resposta_correta": escolhidas.index(correta),
        "explicacao": pergunta.get("explicacao", ""),
    }


# ---- Banco offline Módulo 1 ----
BANCO_M1_ADN = {
    "texto_explicativo": (
        "O ADN (ácido desoxirribonucleico) é a molécula que armazena a informação genética. "
        "É formado por duas cadeias complementares enroladas em dupla hélice, compostas por "
        "nucleótidos (desoxirribose + fosfato + base nitrogenada: adenina, timina, citosina ou guanina). "
        "A complementaridade A-T e C-G permite a replicação semiconservativa e a transcrição para ARN."
    ),
    "perguntas": [
        {
            "pergunta": "Quais são as bases nitrogenadas do ADN?",
            "opcoes": [
                "Adenina, Timina, Citosina e Guanina",
                "Adenina, Uracilo, Citosina e Guanina",
                "Adenina, Timina, Citosina e Uracilo",
                "Adenina, Timina, Ribose e Fosfato",
            ],
            "resposta_correta": 0,
            "explicacao": "O ADN usa A-T e C-G. O uracilo substitui a timina apenas no ARN.",
        },
        {
            "pergunta": "O que é um nucleótido do ADN?",
            "opcoes": [
                "Desoxirribose + fosfato + base nitrogenada",
                "Ribose + fosfato + uracilo",
                "Aminoácido + fosfato + base",
                "Glicose + fosfato + timina",
            ],
            "resposta_correta": 0,
            "explicacao": "Cada nucleótido do ADN tem desoxirribose, um grupo fosfato e uma base (A, T, C ou G).",
        },
    ],
    "fill_in_the_blank": [
        {
            "frase": "O ADN é composto por [___] que contêm as bases nitrogenadas.",
            "palavra_oculta": "nucleótidos",
        },
        {
            "frase": "No ADN, a adenina emparelha sempre com a [___].",
            "palavra_oculta": "timina",
        },
    ],
}

BANCO_M1_SO = {
    "texto_explicativo": (
        "Um Sistema Operativo gere o hardware e fornece serviços às aplicações. "
        "Na gestão de memória, usa paginação (blocos fixos: páginas/frames), segmentação (blocos lógicos) "
        "e memória virtual (swap/paginação por demanda) para isolar processos e otimizar o uso da RAM."
    ),
    "perguntas": [
        {
            "pergunta": "O que é paginação na gestão de memória?",
            "opcoes": [
                "Divisão da memória em blocos fixos (páginas/frames)",
                "Divisão do disco em partições",
                "Técnica de compressão de ficheiros",
                "Protocolo de rede para memória partilhada",
            ],
            "resposta_correta": 0,
            "explicacao": "A paginação divide memória lógica em páginas e física em frames de tamanho fixo.",
        },
        {
            "pergunta": "Para que serve a memória virtual?",
            "opcoes": [
                "Permitir que processos usem mais memória do que a RAM disponível",
                "Aumentar a velocidade do processador",
                "Substituir o sistema de ficheiros",
                "Criar cópias de segurança automáticas",
            ],
            "resposta_correta": 0,
            "explicacao": "A memória virtual combina RAM e disco (swap) para estender o espaço endereçável.",
        },
    ],
    "fill_in_the_blank": [
        {
            "frase": "Na paginação, a memória física é dividida em blocos chamados [___].",
            "palavra_oculta": "frames",
        },
        {
            "frase": "A [___] permite executar processos maiores do que a RAM disponível.",
            "palavra_oculta": "memória virtual",
        },
    ],
}


def gerar_dados_m1_offline(tema: str, num_opcoes: int) -> dict:
    """Gera recurso M1 sem IA: usa banco local ou template genérico honesto."""
    tema = (tema or "").strip() or "este tema"
    t = tema.lower()
    if "adn" in t or "dna" in t or "genét" in t or "genet" in t:
        base = BANCO_M1_ADN
    elif "sistema" in t or "memória" in t or "memoria" in t or "operativo" in t:
        base = BANCO_M1_SO
    else:
        # Genérico: não inventa factos; foca método de estudo do tema
        return {
            "texto_explicativo": (
                f"Recurso DEMO (modo offline) sobre '{tema}'. Sem chave API não é possível "
                "gerar conteúdo factual novo com IA. Utilize este template em aula: 1) definir "
                f"3 conceitos-chave de {tema}; 2) dar um exemplo prático; 3) listar uma dúvida "
                "frequente dos alunos. Para conteúdo factual automático, use o modo Online ou "
                "escolha os temas demo 'ADN' ou 'Sistemas Operativos'."
            ),
            "perguntas": [
                ajustar_num_opcoes(
                    {
                        "pergunta": f"Qual é uma boa estratégia para estudar '{tema}'?",
                        "opcoes": [
                            "Resumir os conceitos-chave e testar-se com perguntas",
                            "Ler uma vez sem apontamentos",
                            "Decorar sem compreender os exemplos",
                            "Estudar apenas na véspera sem revisão",
                        ],
                        "resposta_correta": 0,
                        "explicacao": "Recuperação ativa e resumos são estratégias com evidência de eficácia.",
                    },
                    num_opcoes,
                ),
                ajustar_num_opcoes(
                    {
                        "pergunta": f"Ao explicar '{tema}' a um colega, o que é mais importante?",
                        "opcoes": [
                            "Usar um exemplo concreto e verificar a compreensão",
                            "Usar apenas termos técnicos sem exemplos",
                            "Falar o mais rápido possível",
                            "Evitar perguntas do colega",
                        ],
                        "resposta_correta": 0,
                        "explicacao": "Exemplos concretos e verificação da compreensão consolidam a aprendizagem.",
                    },
                    num_opcoes,
                ),
            ],
            "fill_in_the_blank": [
                {
                    "frase": f"Para dominar {tema}, devo rever os apontamentos com [___].",
                    "palavra_oculta": "regularidade",
                },
                {
                    "frase": "Um bom resumo deve destacar as [___] principais do tema.",
                    "palavra_oculta": "ideias",
                },
            ],
            "_demo_generico": True,
        }
    return {
        "texto_explicativo": base["texto_explicativo"],
        "perguntas": [ajustar_num_opcoes(p, num_opcoes) for p in base["perguntas"]],
        # Cópias para nunca mutar acidentalmente os bancos globais
        "fill_in_the_blank": [dict(lac) for lac in base["fill_in_the_blank"]],
    }


# ---- Banco offline Módulo 2 ----
BANCO_M2_SO = [
    {
        "conceito": "Paging (Paginação)",
        "definicao": "Técnica de gestão de memória que divide a memória em blocos de tamanho fixo (páginas e frames).",
    },
    {
        "conceito": "Memória Virtual",
        "definicao": "Extensão da RAM usando disco (swap), permitindo processos maiores que a memória física.",
    },
    {
        "conceito": "Escalonador (Scheduler)",
        "definicao": "Componente do SO que decide qual processo/thread usa o CPU em cada momento.",
    },
    {
        "conceito": "Deadlock",
        "definicao": "Situação em que dois ou mais processos ficam bloqueados à espera de recursos entre si.",
    },
]

BANCO_M2_ADN = [
    {
        "conceito": "Nucleótido",
        "definicao": "Unidade base do ADN: desoxirribose + fosfato + base nitrogenada (A, T, C ou G).",
    },
    {
        "conceito": "Dupla hélice",
        "definicao": "Estrutura do ADN com duas cadeias complementares enroladas (A-T, C-G).",
    },
    {
        "conceito": "Replicação semiconservativa",
        "definicao": "Cada nova molécula de ADN conserva uma cadeia original e uma cadeia nova.",
    },
    {
        "conceito": "Transcrição",
        "definicao": "Síntese de ARN a partir de um molde de ADN.",
    },
]


def gerar_dados_m2_offline(tema: str) -> dict:
    tema = (tema or "").strip() or "este tema"
    t = tema.lower()
    if "sistema" in t or "memória" in t or "memoria" in t or "operativo" in t:
        return {"pares": [dict(p) for p in BANCO_M2_SO]}
    if "adn" in t or "dna" in t or "genét" in t or "genet" in t:
        return {"pares": [dict(p) for p in BANCO_M2_ADN]}
    return {
        "pares": [
            {"conceito": f"Conceito 1 de {tema}", "definicao": f"Definição introdutória de {tema} (exemplo demo 1)."},
            {"conceito": f"Conceito 2 de {tema}", "definicao": f"Definição intermédia de {tema} (exemplo demo 2)."},
            {"conceito": f"Conceito 3 de {tema}", "definicao": f"Definição avançada de {tema} (exemplo demo 3)."},
            {"conceito": f"Conceito 4 de {tema}", "definicao": f"Aplicação prática de {tema} (exemplo demo 4)."},
        ],
        "_demo_generico": True,
    }


def corrigir_por_keywords(resposta: str, keywords: str) -> dict:
    """Correção local (modo offline): % de palavras-chave encontradas na resposta."""
    lista = [normalizar(k) for k in keywords.split(",") if k.strip()]
    if not lista:
        return {"resultado": "ERRADO", "nota_percentual": 0, "feedback": "Defina palavras-chave para correção."}
    resp = normalizar(resposta)
    encontradas = [k for k in lista if k and k in resp]
    nota = round(len(encontradas) / len(lista) * 100)
    resultado = "CERTO" if nota >= 60 else "ERRADO"
    em_falta = [k for k in lista if k not in encontradas]
    fb = f"Encontrou {len(encontradas)}/{len(lista)} palavras-chave ({', '.join(encontradas) or 'nenhuma'})."
    if em_falta:
        fb += f" Em falta: {', '.join(em_falta)}."
    fb += " (Correção aproximada por palavras-chave — sem análise semântica de IA.)"
    return {"resultado": resultado, "nota_percentual": nota, "feedback": fb}


# ==========================================================
# TEXTOS DA INTERFACE (PT / EN) — chaves idênticas nos 2 idiomas
# ==========================================================
STRINGS = {
    "pt": {
        "role_label": "Papel:",
        "role_teacher": ":material/cast_for_education: Professor",
        "role_student": ":material/backpack: Aluno",
        "mode_label": "Modo de funcionamento:",
        "mode_online": ":material/language: Online (com chave Gemini)",
        "mode_offline": ":material/cloud_off: Offline / Demo (sem chave)",
        "mode_help": "O modo Offline usa um banco local de exemplos e correção sem IA. Ideal para demonstrações sem internet/chave.",
        "model_label": "Modelo de IA Generativa:",
        "model_help": "A lista é obtida da tua própria chave. Recomendados: gemini-3.8-flash (mais recente) ou gemini-3.5-flash-lite (muito económico); gemini-2.5-* para chaves antigas.",
        "model_info": "O modelo Flash é recomendado para rapidez/custo; o Pro para raciocínio analítico.",
        "offline_info": ":material/cloud_off: Modo Offline: sem chamadas à API. Módulos 1 e 2 usam banco local; Módulo 3 usa pergunta manual + palavras-chave.",
        "online_cfg": "Configure o acesso à API do Google Gemini.",
        "api_key_label": "Chave API do Gemini:",
        "api_key_help": "Insira a sua chave API do Google AI Studio. Pode também definir GEMINI_API_KEY nos Secrets.",
        "lib_missing": "Biblioteca `google-genai` não instalada. Corra: `pip install google-genai`",
        "client_ok": "Ligação validada: lista de modelos obtida da tua conta.",
        "model_list_fallback": "Não foi possível listar os modelos da chave (rede ou chave inválida?). A mostrar modelos recomendados.",
        "model_404_hint": "O modelo escolhido já não existe para esta chave — escolhe outro na barra lateral.",
        "gemini_call_err": "Falha na chamada ao Gemini",
        "waiting_key": "Aguardando chave API...",
        "need_key": ":material/arrow_forward: Insira a sua chave API do Gemini na barra lateral **ou** mude para o modo :material/cloud_off: Offline/Demo.",
        "offline_banner": ":material/cloud_off: Está no **modo Offline/Demo**: funciona **sem chave Gemini**, com exemplos locais e correção automática simples (sem IA).",
        "main_title": "EduGen: Gerador e Avaliador Educativo Inteligente",
        "sub_header": "Plataforma interativa para criação automática de recursos didáticos e avaliação assistida por IA — com modo Offline/Demo sem chave.",
        "tab1": ":material/menu_book: Módulo 1: Conteúdo Explicativo, Quiz & Lacunas",
        "tab2": ":material/extension: Módulo 2: Jogo de Associação de Conceitos",
        "tab3": ":material/image: Módulo 3: Avaliação Multimodal & Resposta Aberta",
        "instr": "Responde sempre em português europeu (pt-PT). Mantém exatamente as chaves do JSON pedido.",
        "m1_header": "1. Geração de Conteúdo Didático e Questionário Adaptável",
        "tema_label": "Tema ou Tópico da Aula:",
        "num_opc_label": "Número de opções por pergunta:",
        "btn_gen_m1": "Gerar Recurso Didático Completo",
        "spin_m1": "A gerar texto explicativo, quiz e exercícios de lacunas...",
        "demo_generic_ok": "Recurso demo gerado (offline). Para conteúdo factual escolha 'ADN' ou 'Sistemas Operativos', ou use o modo Online.",
        "demo_bank_ok": "Recurso demo gerado a partir do banco offline!",
        "gen_ok": "Recurso gerado com sucesso!",
        "gen_err": "Erro ao gerar conteúdo: ",
        "bad_json": "A resposta do modelo não é um objeto JSON válido.",
        "client_err": "Erro ao configurar a API do Gemini: ",
        "fix_data": "Limpar dados inválidos",
        "bad_data": "Os dados guardados estão corrompidos. Gere o recurso novamente.",
        "texto_sub": ":material/description: Texto Explicativo (Recurso para o Aluno)",
        "no_text": "(sem texto)",
        "quiz_sub": ":material/quiz: Questionário de Escolha Múltipla",
        "lac_sub": ":material/edit_note: Exercícios de Preenchimento de Lacunas (Fill the Blank)",
        "escolha_label": "Selecione a resposta para a P",
        "lacuna_label": "Palavra para a lacuna ",
        "exercicio": "Exercício ",
        "frase_missing": "(frase em falta)",
        "bad_struct": "ignorada: estrutura inválida recebida do modelo.",
        "lac_no_hidden": "ignorada: sem 'palavra_oculta'.",
        "btn_submit_m1": "Submeter e Corrigir Respostas",
        "result_sub": ":material/assessment: Resultado da Avaliação Automática",
        "no_answer": "Sem resposta. Resposta certa: ",
        "correct": "Correto! ",
        "incorrect": "Incorreto. Resposta certa: ",
        "explic_label": ". Explicação: ",
        "lac_ok": "Certo! ",
        "lac_bad": "Errado. Respondeu ",
        "lac_expected": ", o correto era ",
        "grade_quiz": "Nota Final do Quiz",
        "no_valid": "Sem perguntas válidas para avaliar.",
        "student_no_data": "O professor ainda não gerou este recurso. Aguarde ou peça para gerar.",
        "demo_bank_note": "Nota: o banco demo offline está em português.",
        "m2_header": "2. Jogo de Associação de Conceitos",
        "m2_desc": "Gere dinâmicas interativas onde os estudantes associam termos à respetiva definição pedagógica.",
        "tema_m2_label": "Tema do Jogo de Associação:",
        "btn_create_m2": "Criar Jogo de Associação",
        "spin_m2": "A criar pares conceituais...",
        "jogo_demo_ok": "Jogo demo criado (offline, sem IA)!",
        "jogo_ok": "Jogo criado com sucesso!",
        "jogo_err": "Erro ao gerar jogo: ",
        "bad_game": "Os dados do jogo estão corrompidos. Crie o jogo novamente.",
        "no_pairs": "Nenhum par válido foi gerado.",
        "assoc_sub": ":material/link: Associação de Conceitos",
        "concepts_h": "### Conceitos",
        "defs_h": "### Escolha a Definição Correspondente",
        "def_for": "Definição para ",
        "choose": "-- Selecione --",
        "btn_check_m2": "Verificar Associações",
        "assoc_no_answer": "Sem resposta para ",
        "assoc_good": "corresponde exatamente à definição selecionada.",
        "assoc_bad": "Incorreto para ",
        "assoc_hint": "Reveja a definição correta no material.",
        "assoc_result": "Resultado da Associação",
        "assoc_pairs_ok": "Pares Corretos",
        "m3_header": "3. Avaliação Multimodal com Análise e Correção Semântica por IA",
        "m3_off_info": ":material/cloud_off: Modo Offline: a análise por imagem com IA está indisponível. Use a **pergunta manual + palavras-chave** abaixo.",
        "m3_on_desc": "Carregue uma imagem/recurso visual. A IA formulará uma questão analítica e corrigirá a resposta aberta do aluno.",
        "q_teacher_label": "Pergunta definida pelo professor (sobre a imagem ou tema):",
        "kw_label": "Palavras-chave esperadas (separadas por vírgula):",
        "kw_ph": "ex.: paginação, frames, memória virtual",
        "answer_label": "Resposta do Aluno (Texto Aberto Curto):",
        "btn_correct_off": "Corrigir sem IA (palavras-chave)",
        "ask_question_first": "Defina primeiro a pergunta.",
        "ask_kw_first": "Defina as palavras-chave esperadas antes de corrigir.",
        "ask_answer_first": "Introduza a resposta do aluno antes de submeter.",
        "report_off": ":material/fact_check: Relatório da Avaliação (Offline)",
        "state_good": "ESTADO: RESPOSTA CORRETA",
        "state_bad": "ESTADO: RESPOSTA INCORRETA",
        "score": "Pontuação Atribuída",
        "feedback_label": "Feedback:",
        "upload_label": "Carregar Imagem de Suporte (JPG, PNG):",
        "img_caption": "Recurso Visual do Professor",
        "btn_gen_q": "Gerar Pergunta Analítica sobre a Imagem",
        "spin_img": "A analisar o conteúdo visual e a elaborar a pergunta...",
        "img_open_err": "Não foi possível abrir a imagem: ",
        "ia_no_question": "A IA não devolveu nenhuma pergunta. Tente novamente.",
        "gen_q_err": "Erro ao gerar pergunta: ",
        "generated_q": "Pergunta Gerada pela IA: ",
        "btn_eval": "Avaliar e Corrigir Resposta com IA",
        "spin_eval": "A IA está a analisar semanticamente a resposta do aluno...",
        "eval_err": "Erro ao corrigir resposta: ",
        "report_ia": ":material/fact_check: Relatório da Avaliação Inteligente",
        "feedback_ia": "Feedback Pedagógico da IA: ",
        "need_answer": "Por favor, introduza uma resposta antes de submeter para avaliação.",
        "ed_title": ":material/edit: Editor offline (Professor)",
        "ed_load": "Carregar base demo para editar",
        "ed_text_label": "Texto explicativo (pode editar):",
        "ed_save_text": "Guardar texto",
        "ed_text_ok": "Texto atualizado!",
        "ed_q_new": "Nova pergunta de escolha múltipla",
        "ed_q_text": "Enunciado:",
        "ed_q_opts": "Opções (uma por linha, mínimo 2):",
        "ed_q_correct": "Nº da opção correta (começa em 1):",
        "ed_q_expl": "Explicação:",
        "ed_q_add": "Adicionar pergunta",
        "ed_q_ok": "Pergunta adicionada!",
        "ed_q_err": "Preencha o enunciado, pelo menos 2 opções e um número válido.",
        "ed_l_new": "Nova lacuna",
        "ed_l_phrase": "Frase com [___] a marcar a lacuna:",
        "ed_l_word": "Palavra correta:",
        "ed_l_add": "Adicionar lacuna",
        "ed_l_ok": "Lacuna adicionada!",
        "ed_l_err": "Preencha a frase e a palavra correta.",
        "ed_l_nomarker": "A frase deve conter o marcador [___].",
        "ed_reset": "Repor base demo",
        "ed_reset_ok": "Base demo reposta.",
        "menu_about": "Sobre o EduGen OS",
        "menu_new": "Novo",
        "menu_clear_answers": "Limpar respostas",
        "menu_clear_data": "Apagar recursos",
        "menu_to_pt": "Português",
        "menu_to_en": "English",
        "menu_to_teacher": "Professor",
        "menu_to_student": "Aluno",
        "menu_to_online": "Online",
        "menu_to_offline": "Offline",
        "menu_restart": "Reiniciar sessão",
        "about_title": "Sobre o EduGen OS",
        "about_body": "**EduGen OS 1.0** — edição retro.\n\nGerador e avaliador educativo com IA (Gemini) e modo offline sem chave.\n\n- Módulos 1, 2 e 3: conteúdo, jogo e avaliação multimodal\n- Papéis Professor/Aluno · PT/EN",
        "about_close": "Fechar",
    },
    "en": {
        "role_label": "Role:",
        "role_teacher": ":material/cast_for_education: Teacher",
        "role_student": ":material/backpack: Student",
        "mode_label": "Operation mode:",
        "mode_online": ":material/language: Online (with Gemini key)",
        "mode_offline": ":material/cloud_off: Offline / Demo (no key)",
        "mode_help": "Offline mode uses a local bank of examples and non-AI correction. Ideal for demos without internet/key.",
        "model_label": "Generative AI Model:",
        "model_help": "The list is fetched from your own key. Recommended: gemini-3.8-flash (latest) or gemini-3.5-flash-lite (very cheap); gemini-2.5-* for older keys.",
        "model_info": "The Flash model is recommended for speed/cost; Pro for analytical reasoning.",
        "offline_info": ":material/cloud_off: Offline mode: no API calls. Modules 1 and 2 use a local bank; Module 3 uses manual question + keywords.",
        "online_cfg": "Configure Google Gemini API access.",
        "api_key_label": "Gemini API Key:",
        "api_key_help": "Enter your Google AI Studio API key. You can also set GEMINI_API_KEY in Secrets.",
        "lib_missing": "Library `google-genai` not installed. Run: `pip install google-genai`",
        "client_ok": "Connection validated: model list fetched from your account.",
        "model_list_fallback": "Couldn't fetch the model list for this key (network or invalid key?). Showing recommended models.",
        "model_404_hint": "The selected model no longer exists for this key — pick another one in the sidebar.",
        "gemini_call_err": "Gemini call failed",
        "waiting_key": "Waiting for API key...",
        "need_key": ":material/arrow_forward: Enter your Gemini API key in the sidebar **or** switch to :material/cloud_off: Offline/Demo mode.",
        "offline_banner": ":material/cloud_off: You are in **Offline/Demo mode**: works **without a Gemini key**, with local examples and simple automatic correction (no AI).",
        "main_title": "EduGen: Intelligent Educational Generator & Evaluator",
        "sub_header": "Interactive platform for automatic teaching-resource creation and AI-assisted assessment — with keyless Offline/Demo mode.",
        "tab1": ":material/menu_book: Module 1: Explanatory Content, Quiz & Gaps",
        "tab2": ":material/extension: Module 2: Concept-Matching Game",
        "tab3": ":material/image: Module 3: Multimodal Assessment & Open Answer",
        "instr": "Always answer in English. Keep exactly the requested JSON keys.",
        "m1_header": "1. Teaching Content Generation and Adaptive Quiz",
        "tema_label": "Lesson Theme or Topic:",
        "num_opc_label": "Number of options per question:",
        "btn_gen_m1": "Generate Full Teaching Resource",
        "spin_m1": "Generating explanatory text, quiz and gap exercises...",
        "demo_generic_ok": "Demo resource generated (offline). For factual content choose 'ADN' or 'Sistemas Operativos', or use Online mode.",
        "demo_bank_ok": "Demo resource generated from the offline bank!",
        "gen_ok": "Resource generated successfully!",
        "gen_err": "Error generating content: ",
        "bad_json": "The model response is not a valid JSON object.",
        "client_err": "Error configuring the Gemini API: ",
        "fix_data": "Clear invalid data",
        "bad_data": "Stored data is corrupted. Please generate the resource again.",
        "texto_sub": ":material/description: Explanatory Text (Student Resource)",
        "no_text": "(no text)",
        "quiz_sub": ":material/quiz: Multiple-Choice Quiz",
        "lac_sub": ":material/edit_note: Fill-in-the-Blank Exercises",
        "escolha_label": "Select the answer for Q",
        "lacuna_label": "Word for gap ",
        "exercicio": "Exercise ",
        "frase_missing": "(missing sentence)",
        "bad_struct": "skipped: invalid structure received from the model.",
        "lac_no_hidden": "skipped: no 'palavra_oculta'.",
        "btn_submit_m1": "Submit and Check Answers",
        "result_sub": ":material/assessment: Automatic Assessment Result",
        "no_answer": "No answer. Correct answer: ",
        "correct": "Correct! ",
        "incorrect": "Incorrect. Correct answer: ",
        "explic_label": ". Explanation: ",
        "lac_ok": "Correct! ",
        "lac_bad": "Wrong. You answered ",
        "lac_expected": ", the correct answer was ",
        "grade_quiz": "Final Quiz Grade",
        "no_valid": "No valid questions to assess.",
        "student_no_data": "The teacher has not generated this resource yet. Please wait or ask them to generate it.",
        "demo_bank_note": "Note: the offline demo bank is in Portuguese.",
        "m2_header": "2. Concept-Matching Game",
        "m2_desc": "Generate interactive dynamics where students match terms to their pedagogical definition.",
        "tema_m2_label": "Matching Game Theme:",
        "btn_create_m2": "Create Matching Game",
        "spin_m2": "Creating concept pairs...",
        "jogo_demo_ok": "Demo game created (offline, no AI)!",
        "jogo_ok": "Game created successfully!",
        "jogo_err": "Error generating game: ",
        "bad_game": "Game data is corrupted. Please create the game again.",
        "no_pairs": "No valid pairs were generated.",
        "assoc_sub": ":material/link: Concept Matching",
        "concepts_h": "### Concepts",
        "defs_h": "### Choose the Matching Definition",
        "def_for": "Definition for ",
        "choose": "-- Select --",
        "btn_check_m2": "Check Matches",
        "assoc_no_answer": "No answer for ",
        "assoc_good": "matches the selected definition exactly.",
        "assoc_bad": "Incorrect for ",
        "assoc_hint": "Review the correct definition in the material.",
        "assoc_result": "Matching Result",
        "assoc_pairs_ok": "Correct Pairs",
        "m3_header": "3. Multimodal Assessment with AI Semantic Correction",
        "m3_off_info": ":material/cloud_off: Offline mode: AI image analysis is unavailable. Use the **manual question + keywords** below.",
        "m3_on_desc": "Upload an image/visual resource. The AI will formulate an analytical question and grade the student's open answer.",
        "q_teacher_label": "Teacher-defined question (about the image or theme):",
        "kw_label": "Expected keywords (comma-separated):",
        "kw_ph": "e.g.: paging, frames, virtual memory",
        "answer_label": "Student Answer (Short Open Text):",
        "btn_correct_off": "Check without AI (keywords)",
        "ask_question_first": "Define the question first.",
        "ask_kw_first": "Define the expected keywords before checking.",
        "ask_answer_first": "Enter the student answer before submitting.",
        "report_off": ":material/fact_check: Assessment Report (Offline)",
        "state_good": "STATUS: CORRECT ANSWER",
        "state_bad": "STATUS: INCORRECT ANSWER",
        "score": "Assigned Score",
        "feedback_label": "Feedback:",
        "upload_label": "Upload Support Image (JPG, PNG):",
        "img_caption": "Teacher Visual Resource",
        "btn_gen_q": "Generate Analytical Question about the Image",
        "spin_img": "Analysing the visual content and drafting the question...",
        "img_open_err": "Could not open the image: ",
        "ia_no_question": "The AI returned no question. Please try again.",
        "gen_q_err": "Error generating question: ",
        "generated_q": "AI-Generated Question: ",
        "btn_eval": "Assess and Correct Answer with AI",
        "spin_eval": "The AI is semantically analysing the student answer...",
        "eval_err": "Error correcting answer: ",
        "report_ia": ":material/fact_check: Intelligent Assessment Report",
        "feedback_ia": "AI Pedagogical Feedback: ",
        "need_answer": "Please enter an answer before submitting for assessment.",
        "ed_title": ":material/edit: Offline editor (Teacher)",
        "ed_load": "Load demo base for editing",
        "ed_text_label": "Explanatory text (editable):",
        "ed_save_text": "Save text",
        "ed_text_ok": "Text updated!",
        "ed_q_new": "New multiple-choice question",
        "ed_q_text": "Prompt:",
        "ed_q_opts": "Options (one per line, minimum 2):",
        "ed_q_correct": "Correct option number (starts at 1):",
        "ed_q_expl": "Explanation:",
        "ed_q_add": "Add question",
        "ed_q_ok": "Question added!",
        "ed_q_err": "Fill in the prompt, at least 2 options and a valid number.",
        "ed_l_new": "New gap",
        "ed_l_phrase": "Sentence with [___] marking the gap:",
        "ed_l_word": "Correct word:",
        "ed_l_add": "Add gap",
        "ed_l_ok": "Gap added!",
        "ed_l_err": "Fill in the sentence and the correct word.",
        "ed_l_nomarker": "The sentence must contain the [___] marker.",
        "ed_reset": "Restore demo base",
        "ed_reset_ok": "Demo base restored.",
        "menu_about": "About EduGen OS",
        "menu_new": "New",
        "menu_clear_answers": "Clear answers",
        "menu_clear_data": "Delete resources",
        "menu_to_pt": "Português",
        "menu_to_en": "English",
        "menu_to_teacher": "Teacher",
        "menu_to_student": "Student",
        "menu_to_online": "Online",
        "menu_to_offline": "Offline",
        "menu_restart": "Restart session",
        "about_title": "About EduGen OS",
        "about_body": "**EduGen OS 1.0** — retro edition.\n\nAI-powered (Gemini) teaching generator and evaluator with keyless offline mode.\n\n- Modules 1, 2 and 3: content, game and multimodal assessment\n- Teacher/Student roles · PT/EN",
        "about_close": "Close",
    },
}


# ---- Modelos Gemini: recomendados + lista real obtida da chave ----
# (os nomes mudam com o tempo — a app lista os modelos da própria chave
# e usa esta lista apenas como ordenação/preferência e fallback)
MODELOS_RECOMENDADOS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
]


def ordenar_modelos(disponiveis, limite: int = 30) -> list:
    """Recomendados primeiro (na ordem definida), restantes por ordem alfabética."""
    unicos = []
    for m in disponiveis or []:
        if isinstance(m, str) and m and m not in unicos:
            unicos.append(m)
    pref = [m for m in MODELOS_RECOMENDADOS if m in unicos]
    resto = sorted(m for m in unicos if m not in pref)
    return (pref + resto)[:limite]


def listar_modelos_disponiveis(client) -> list | None:
    """Modelos com generateContent visíveis para a chave; None se não for possível listar."""
    try:
        nomes = []
        for m in client.models.list():
            nome = str(getattr(m, "name", "") or "").removeprefix("models/")
            acoes = getattr(m, "supported_actions", None) or []
            if nome and (not acoes or "generateContent" in acoes):
                nomes.append(nome)
        return nomes or None
    except Exception:
        return None


def modelo_indisponivel(erro) -> bool:
    """True se o erro for de modelo inexistente/retirado (404 NOT_FOUND)."""
    t = str(erro).lower()
    return "not_found" in t or "not found" in t or "no longer available" in t


# ==========================================================
# BARRA LATERAL - IDIOMA, PAPEL E MODO ONLINE / OFFLINE
# ==========================================================
with st.sidebar:
    st.markdown(
        '<div class="mac-panel-title"><span>Control Panel</span></div>',
        unsafe_allow_html=True,
    )

    lang_nome = st.radio("Idioma / Language:", ["Português", "English"], index=0, key="lang")
    LANG = "en" if lang_nome == "English" else "pt"
    STR = STRINGS[LANG]
    INSTR = STR["instr"]

    papel = st.radio(
        STR["role_label"],
        ["teacher", "student"],
        format_func=lambda k: STR["role_teacher"] if k == "teacher" else STR["role_student"],
        index=0,
        key="papel",
    )
    # Valores estáveis (independentes do idioma): mudar de idioma nunca
    # invalida a seleção guardada, por isso o modo/papel nunca saltam sozinhos.
    is_student = (papel == "student")

    modo = st.radio(
        STR["mode_label"],
        ["online", "offline"],
        format_func=lambda k: STR["mode_online"] if k == "online" else STR["mode_offline"],
        index=0,
        key="modo",
        help=STR["mode_help"],
    )
    offline = (modo == "offline")

    client = None
    api_key = ""
    modelo_selecionado = MODELOS_RECOMENDADOS[0]

    if offline:
        st.info(STR["offline_info"])
    else:
        st.markdown(STR["online_cfg"])
        # Permite chave via Secrets/ambiente (não só sidebar)
        chave_sugerida = ""
        try:
            chave_sugerida = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            chave_sugerida = ""
        chave_sugerida = chave_sugerida or os.getenv("GEMINI_API_KEY", "")

        api_key = st.text_input(
            STR["api_key_label"],
            value=chave_sugerida,
            type="password",
            help=STR["api_key_help"],
        )

        if not GEMINI_LIB_DISPONIVEL:
            st.error(STR["lib_missing"])
        elif api_key:
            try:
                client = genai.Client(api_key=api_key)
            except Exception as exc:
                st.error(f"{STR['client_err']}{exc}")
                client = None

            if client is not None:
                # A lista de modelos vem da própria chave (em cache por chave):
                # nunca fica desatualizada como uma lista fixa. Sem lista,
                # apresenta-se os recomendados.
                if st.session_state.get("_modelos_para") != api_key:
                    listados = listar_modelos_disponiveis(client)
                    st.session_state["_modelos_para"] = api_key
                    st.session_state["_modelos_lista"] = (
                        ordenar_modelos(listados) if listados else list(MODELOS_RECOMENDADOS)
                    )
                    st.session_state["_modelos_fallback"] = listados is None
                    if st.session_state.get("modelo") not in st.session_state["_modelos_lista"]:
                        st.session_state["modelo"] = st.session_state["_modelos_lista"][0]

                if st.session_state.get("_modelos_fallback"):
                    st.warning(STR["model_list_fallback"])
                else:
                    st.success(STR["client_ok"])

                modelo_selecionado = st.selectbox(
                    STR["model_label"],
                    st.session_state["_modelos_lista"],
                    index=0,
                    key="modelo",
                    help=STR["model_help"],
                )
        else:
            st.warning(STR["waiting_key"])

    st.divider()
    if not offline:
        st.info(STR["model_info"])

# ==========================================================
# MENU BAR FUNCIONAL (EduGen OS / File / Edit / View / Special)
# ==========================================================
@st.dialog(STR["about_title"])
def about_dialog():
    st.markdown(STR["about_body"])
    if st.button(STR["about_close"], key="about_close", icon=":material/close:"):
        st.rerun()


def menu_go(widget_key: str, value: str):
    """Troca idioma/papel/modo via menu; aplica no próximo run (antes dos widgets)."""
    st.session_state["_pending_widget"] = (widget_key, value)
    st.rerun()


def menu_novo():
    """File > Novo: limpa recursos, respostas e pergunta multimodal."""
    for k in ("dados_m1", "dados_m2", "pergunta_multimodal", "img_bytes", "_img_id"):
        st.session_state.pop(k, None)
    limpar_respostas_antigas()


c_brand, c_file, c_edit, c_view, c_special, c_ver = st.columns(
    [1.5, 0.7, 0.7, 0.8, 0.9, 1.4], vertical_alignment="center"
)
with c_brand:
    ch_brand = st.menu_button("EduGen OS", [STR["menu_about"]], type="tertiary", key="menu_brand")
with c_file:
    ch_file = st.menu_button("File", [STR["menu_new"]], type="tertiary", key="menu_file")
with c_edit:
    ch_edit = st.menu_button(
        "Edit",
        [STR["menu_clear_answers"], STR["menu_clear_data"]],
        type="tertiary",
        key="menu_edit",
    )
with c_view:
    ch_view = st.menu_button(
        "View",
        [
            STR["menu_to_pt"],
            STR["menu_to_en"],
            STR["menu_to_teacher"],
            STR["menu_to_student"],
            STR["menu_to_online"],
            STR["menu_to_offline"],
        ],
        type="tertiary",
        key="menu_view",
    )
with c_special:
    ch_special = st.menu_button("Special", [STR["menu_restart"]], type="tertiary", key="menu_special")
with c_ver:
    st.markdown('<div style="text-align: right;">System 6.0.8</div>', unsafe_allow_html=True)

if ch_brand == STR["menu_about"]:
    about_dialog()
elif ch_file == STR["menu_new"]:
    menu_novo()
elif ch_edit == STR["menu_clear_answers"]:
    limpar_respostas_antigas()
elif ch_edit == STR["menu_clear_data"]:
    st.session_state.pop("dados_m1", None)
    st.session_state.pop("dados_m2", None)
    limpar_respostas_antigas()
elif ch_view in (STR["menu_to_pt"], STR["menu_to_en"]):
    menu_go("lang", "Português" if ch_view == STR["menu_to_pt"] else "English")
elif ch_view in (STR["menu_to_teacher"], STR["menu_to_student"]):
    menu_go("papel", "teacher" if ch_view == STR["menu_to_teacher"] else "student")
elif ch_view in (STR["menu_to_online"], STR["menu_to_offline"]):
    menu_go("modo", "online" if ch_view == STR["menu_to_online"] else "offline")
elif ch_special == STR["menu_restart"]:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


st.markdown(
    f"""<div class="mac-window">
    <div class="mac-titlebar"><div class="mac-title">EduGen</div></div>
    <div class="mac-body">
        <div class="main-header">{STR["main_title"]}</div>
        <div class="sub-header">{STR["sub_header"]}</div>
    </div>
</div>""",
    unsafe_allow_html=True,
)

if offline:
    st.warning(STR["offline_banner"])
    model_name = None
else:
    if not api_key or client is None:
        st.info(STR["need_key"])
        st.stop()
    model_name = modelo_selecionado


def gerar_com_gemini(prompt, usar_json: bool = False):
    """Wrapper com tratamento de erros e parse JSON seguro."""
    try:
        cfg = types.GenerateContentConfig(response_mime_type="application/json") if usar_json else None
        res = client.models.generate_content(model=model_name, contents=prompt, config=cfg)
        return res.text
    except Exception as e:
        dica = f" {STR['model_404_hint']}" if modelo_indisponivel(e) else ""
        raise RuntimeError(f"{STR['gemini_call_err']} ({model_name}): {e}{dica}") from e


def avaliar_resposta_aberta(img_bytes: bytes, pergunta: str, resposta: str):
    """Envia pergunta+resposta+imagem ao Gemini e mostra o relatório. Usado por ambos os papéis."""
    prompt_correcao = f"""
    {INSTR}

    Atua como um professor rigoroso / Act as a rigorous teacher.

    Pergunta colocada ao aluno / Question asked:
    \"\"\"{pergunta}\"\"\"

    Resposta fornecida pelo aluno / Student answer:
    \"\"\"{resposta}\"\"\"

    Avalia a resposta do aluno tendo em conta o rigor concetual / Grade for conceptual rigour.
    Retorna um JSON estrito contendo / Return strict JSON with:
    1. 'resultado': Apenas 'CERTO' ou 'ERRADO'.
    2. 'nota_percentual': Número inteiro de 0 a 100.
    3. 'feedback_pedagogico': Explicação construtiva de 2 a 3 frases dirigida ao aluno.

    Formato JSON:
    {{
      "resultado": "CERTO",
      "nota_percentual": 85,
      "feedback_pedagogico": "..."
    }}
    """
    try:
        res_corr = client.models.generate_content(
            model=model_name,
            contents=[
                prompt_correcao,
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        dados_corr = extrair_json_seguro(res_corr.text)
        if not isinstance(dados_corr, dict):
            raise ValueError(STR["bad_json"])
        nota = parse_nota_percentual(dados_corr.get("nota_percentual", 0))
        resultado = str(dados_corr.get("resultado", "ERRADO")).strip().upper()

        st.divider()
        st.subheader(STR["report_ia"])
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if resultado == "CERTO":
                st.markdown(f"<div class='correct-badge'>{STR['state_good']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='incorrect-badge'>{STR['state_bad']}</div>", unsafe_allow_html=True)
        with col_r2:
            st.metric(STR["score"], f"{nota}%")
        st.markdown(f"**{STR['feedback_ia']}** {dados_corr.get('feedback_pedagogico', '')}")
    except Exception as e:
        dica = f" {STR['model_404_hint']}" if modelo_indisponivel(e) else ""
        st.error(f"{STR['eval_err']}{e}{dica}")


# ==========================================================
# ABAS
# ==========================================================
tab1, tab2, tab3 = st.tabs([STR["tab1"], STR["tab2"], STR["tab3"]])

# ----------------------------------------------------------
# MÓDULO 1
# ----------------------------------------------------------
with tab1:
    st.header(STR["m1_header"])

    col_input1, col_input2 = st.columns([2, 1])
    with col_input1:
        tema_m1 = st.text_input(STR["tema_label"], value="Estrutura e Funcionalidades do ADN", key="tema_m1")
    with col_input2:
        num_opcoes = st.slider(STR["num_opc_label"], min_value=2, max_value=6, value=4, key="num_opc")

    if not is_student and st.button(STR["btn_gen_m1"], icon=":material/auto_awesome:", key="btn_m1"):
        with st.spinner(STR["spin_m1"]):
            limpar_respostas_antigas(prefixos=("q_", "lac_"))
            if offline:
                dados_m1 = gerar_dados_m1_offline(tema_m1, num_opcoes)
                st.session_state["dados_m1"] = dados_m1
                if dados_m1.get("_demo_generico"):
                    st.success(STR["demo_generic_ok"])
                else:
                    st.success(STR["demo_bank_ok"])
                if LANG == "en":
                    st.info(STR["demo_bank_note"])
            else:
                prompt_m1 = f"""
                {INSTR}
                Atua como um professor e especialista pedagógico no tema '{tema_m1}' / Act as a teacher on '{tema_m1}'.
                Gera um recurso educativo completo em formato JSON estrito contendo:
                1. 'texto_explicativo': Um resumo pedagógico e rigoroso sobre o tema (aproximadamente 200 palavras).
                2. 'perguntas': Uma lista de 2 perguntas de escolha múltipla. Cada pergunta deve ter exatamente {num_opcoes} opções de resposta, um índice de 'resposta_correta' (inteiro 0 a {num_opcoes - 1}) e uma 'explicacao' da solução.
                3. 'fill_in_the_blank': 2 frases com uma lacuna marcada como '[___]', a palavra correta para preencher a lacuna ('palavra_oculta') e o contexto.

                Responde EXCLUSIVAMENTE em formato JSON válido com a seguinte estrutura:
                {{
                  "texto_explicativo": "...",
                  "perguntas": [
                    {{
                      "pergunta": "...",
                      "opcoes": ["...", "..."],
                      "resposta_correta": 0,
                      "explicacao": "..."
                    }}
                  ],
                  "fill_in_the_blank": [
                    {{
                      "frase": "O ADN é composto por [___] que contêm as bases nitrogenadas.",
                      "palavra_oculta": "nucleótidos"
                    }}
                  ]
                }}
                """
                try:
                    texto = gerar_com_gemini(prompt_m1, usar_json=True)
                    dados_m1 = extrair_json_seguro(texto)
                    if not isinstance(dados_m1, dict):
                        raise ValueError(STR["bad_json"])
                    st.session_state["dados_m1"] = dados_m1
                    st.success(STR["gen_ok"])
                except Exception as e:
                    st.error(f"{STR['gen_err']}{e}")

    # ---- Editor offline (só Professor, só Offline) ----
    if offline and not is_student:
        with st.expander(STR["ed_title"]):
            if "dados_m1" not in st.session_state:
                if st.button(STR["ed_load"], icon=":material/download:", key="ed_load"):
                    st.session_state["dados_m1"] = gerar_dados_m1_offline(tema_m1, num_opcoes)
                    st.rerun()
            else:
                d_ed = st.session_state["dados_m1"]
                if not isinstance(d_ed, dict):
                    st.error(STR["bad_data"])
                else:
                    novo_texto = st.text_area(
                        STR["ed_text_label"],
                        value=str(d_ed.get("texto_explicativo", "")),
                        key="ed_texto",
                        height=100,
                    )
                    if st.button(STR["ed_save_text"], icon=":material/save:", key="ed_save_text"):
                        d_ed["texto_explicativo"] = novo_texto
                        st.success(STR["ed_text_ok"])

                    st.markdown(f"**{STR['ed_q_new']}**")
                    eq = st.text_input(STR["ed_q_text"], key="ed_q")
                    eopts = st.text_area(STR["ed_q_opts"], key="ed_opts", height=100)
                    ecorr = st.number_input(STR["ed_q_correct"], min_value=1, max_value=10, value=1, step=1, key="ed_corr")
                    eexpl = st.text_input(STR["ed_q_expl"], key="ed_expl")
                    if st.button(STR["ed_q_add"], icon=":material/add:", key="ed_q_add"):
                        opts = [o.strip() for o in eopts.splitlines() if o.strip()]
                        if not eq.strip() or len(opts) < 2 or not (1 <= int(ecorr) <= len(opts)):
                            st.error(STR["ed_q_err"])
                        else:
                            if not isinstance(d_ed.get("perguntas"), list):
                                d_ed["perguntas"] = []
                            d_ed["perguntas"].append(
                                {
                                    "pergunta": eq.strip(),
                                    "opcoes": opts,
                                    "resposta_correta": int(ecorr) - 1,
                                    "explicacao": eexpl.strip(),
                                }
                            )
                            limpar_chaves_resposta_m1()
                            st.success(STR["ed_q_ok"])

                    st.markdown(f"**{STR['ed_l_new']}**")
                    ef = st.text_input(STR["ed_l_phrase"], key="ed_f")
                    ew = st.text_input(STR["ed_l_word"], key="ed_w")
                    if st.button(STR["ed_l_add"], icon=":material/add:", key="ed_l_add"):
                        if not ef.strip() or not ew.strip():
                            st.error(STR["ed_l_err"])
                        elif "[___]" not in ef:
                            st.error(STR["ed_l_nomarker"])
                        else:
                            if not isinstance(d_ed.get("fill_in_the_blank"), list):
                                d_ed["fill_in_the_blank"] = []
                            d_ed["fill_in_the_blank"].append({"frase": ef.strip(), "palavra_oculta": ew.strip()})
                            limpar_chaves_resposta_m1()
                            st.success(STR["ed_l_ok"])

                    if st.button(STR["ed_reset"], icon=":material/restart_alt:", key="ed_reset"):
                        st.session_state["dados_m1"] = gerar_dados_m1_offline(tema_m1, num_opcoes)
                        limpar_chaves_resposta_m1()
                        st.success(STR["ed_reset_ok"])

    if "dados_m1" not in st.session_state:
        if is_student:
            st.info(STR["student_no_data"])
    else:
        dados = st.session_state["dados_m1"]
        if not isinstance(dados, dict):
            st.error(STR["bad_data"])
            if st.button(STR["fix_data"], icon=":material/delete:", key="fix_m1"):
                st.session_state.pop("dados_m1", None)
                st.rerun()
            st.stop()
        perguntas = dados.get("perguntas", []) or []
        lacunas = dados.get("fill_in_the_blank", []) or []
        if not isinstance(perguntas, list):
            perguntas = []
        if not isinstance(lacunas, list):
            lacunas = []

        st.subheader(STR["texto_sub"])
        st.info(dados.get("texto_explicativo", STR["no_text"]))

        st.subheader(STR["quiz_sub"])
        respostas_aluno_m1 = {}
        perguntas_validas = []
        for idx, q in enumerate(perguntas):
            if not pergunta_valida(q):
                st.warning(f"P{idx + 1} {STR['bad_struct']}")
                continue
            enunciado = q.get("pergunta", f"Pergunta {idx + 1}")
            if not isinstance(enunciado, str):
                enunciado = str(enunciado)
            opcoes = q["opcoes"]
            perguntas_validas.append((idx, q))
            st.markdown(f"**P{idx + 1}: {enunciado}**")
            respostas_aluno_m1[idx] = st.radio(
                f"{STR['escolha_label']}{idx + 1}:",
                opcoes,
                index=None,
                key=f"q_{idx}",
            )

        st.subheader(STR["lac_sub"])
        respostas_lacunas = {}
        for idx_l, lacuna in enumerate(lacunas):
            if not isinstance(lacuna, dict):
                st.warning(f"{STR['exercicio']}{idx_l + 1} {STR['bad_struct']}")
                continue
            frase = lacuna.get("frase", STR["frase_missing"])
            if "palavra_oculta" not in lacuna:
                st.warning(f"{STR['exercicio']}{idx_l + 1} {STR['lac_no_hidden']}")
                continue
            st.write(f"**{STR['exercicio']}{idx_l + 1}:** {frase}")
            respostas_lacunas[idx_l] = st.text_input(f"{STR['lacuna_label']}{idx_l + 1}:", key=f"lac_{idx_l}")

        if st.button(STR["btn_submit_m1"], icon=":material/check_circle:", key="btn_validar_m1"):
            st.divider()
            st.subheader(STR["result_sub"])

            acertos_quiz = 0
            for idx, q in perguntas_validas:
                resp_correta_texto = q["opcoes"][q["resposta_correta"]]
                escolha = respostas_aluno_m1.get(idx)
                if escolha is None:
                    st.markdown(
                        f"<div class='incorrect-badge'>P{idx + 1}: {STR['no_answer']}'{resp_correta_texto}'.</div>",
                        unsafe_allow_html=True,
                    )
                elif escolha == resp_correta_texto:
                    acertos_quiz += 1
                    st.markdown(
                        f"<div class='correct-badge'>P{idx + 1}: {STR['correct']}{q.get('explicacao', '')}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='incorrect-badge'>P{idx + 1}: {STR['incorrect']}'{resp_correta_texto}'{STR['explic_label']}{q.get('explicacao', '')}</div>",
                        unsafe_allow_html=True,
                    )

            acertos_lacunas = 0
            lacunas_validas = 0
            for idx_l, lacuna in enumerate(lacunas):
                if not isinstance(lacuna, dict) or "palavra_oculta" not in lacuna:
                    continue
                lacunas_validas += 1
                palavra_user = normalizar(respostas_lacunas.get(idx_l, ""))
                palavra_certa = normalizar(lacuna["palavra_oculta"])
                if palavra_user and palavra_user == palavra_certa:
                    acertos_lacunas += 1
                    st.success(f"{STR['exercicio']}{idx_l + 1}: {STR['lac_ok']}('{lacuna['palavra_oculta']}')")
                else:
                    st.error(
                        f"{STR['exercicio']}{idx_l + 1}: {STR['lac_bad']}'{respostas_lacunas.get(idx_l, '')}'{STR['lac_expected']}'{lacuna['palavra_oculta']}'."
                    )

            total = len(perguntas_validas) + lacunas_validas
            if total == 0:
                st.warning(STR["no_valid"])
            else:
                st.metric(STR["grade_quiz"], f"{((acertos_quiz + acertos_lacunas) / total) * 100:.0f}%")

# ----------------------------------------------------------
# MÓDULO 2
# ----------------------------------------------------------
with tab2:
    st.header(STR["m2_header"])
    st.markdown(STR["m2_desc"])

    tema_m2 = st.text_input(STR["tema_m2_label"], value="Sistemas Operativos e Gestão de Memória", key="tema_m2")

    if not is_student and st.button(STR["btn_create_m2"], icon=":material/auto_awesome:", key="btn_m2"):
        with st.spinner(STR["spin_m2"]):
            limpar_respostas_antigas(prefixos=("assoc_",), extras=("def_baralhadas",))
            if offline:
                st.session_state["dados_m2"] = gerar_dados_m2_offline(tema_m2)
                st.success(STR["jogo_demo_ok"])
                if LANG == "en":
                    st.info(STR["demo_bank_note"])
            else:
                prompt_m2 = f"""
                {INSTR}
                Cria um jogo de associação sobre o tema '{tema_m2}' / Create a matching game about '{tema_m2}'.
                Gera exatamente 4 pares de Conceito e Definição em JSON estrito.
                Estrutura exigida:
                {{
                  "pares": [
                    {{"conceito": "Paging", "definicao": "Técnica de gestão de memória que divide a memória física em blocos de tamanho fixo chamados frames."}},
                    ...
                  ]
                }}
                """
                try:
                    texto = gerar_com_gemini(prompt_m2, usar_json=True)
                    dados_m2 = extrair_json_seguro(texto)
                    if not isinstance(dados_m2, dict):
                        raise ValueError(STR["bad_json"])
                    st.session_state["dados_m2"] = dados_m2
                    st.success(STR["jogo_ok"])
                except Exception as e:
                    st.error(f"{STR['jogo_err']}{e}")

    if "dados_m2" not in st.session_state:
        if is_student:
            st.info(STR["student_no_data"])
    else:
        dados_m2 = st.session_state["dados_m2"]
        if not isinstance(dados_m2, dict):
            st.error(STR["bad_game"])
            if st.button(STR["fix_data"], icon=":material/delete:", key="fix_m2"):
                st.session_state.pop("dados_m2", None)
                st.rerun()
            st.stop()
        pares = [p for p in dados_m2.get("pares", []) if par_valido(p)]
        if not pares:
            st.warning(STR["no_pairs"])
        else:
            st.subheader(STR["assoc_sub"])
            conceitos = [p["conceito"] for p in pares]
            definicoes = [p["definicao"] for p in pares]
            # Baralha uma única vez e guarda em session_state (evita re-baralhar a cada rerun).
            # Re-baralha se o conteúdo mudou, não apenas o tamanho.
            guardadas = st.session_state.get("def_baralhadas")
            if not isinstance(guardadas, list) or sorted(map(str, guardadas)) != sorted(map(str, definicoes)):
                st.session_state["def_baralhadas"] = random.sample(definicoes, len(definicoes))
            definicoes_baralhadas = st.session_state["def_baralhadas"]

            respostas_assoc = {}
            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown(STR["concepts_h"])
                for idx, c in enumerate(conceitos):
                    st.info(f"**{idx + 1}. {c}**")
            with col_d:
                st.markdown(STR["defs_h"])
                for idx, c in enumerate(conceitos):
                    # Indexado por posição (não pelo conceito) para suportar conceitos duplicados
                    respostas_assoc[idx] = st.selectbox(
                        f"{STR['def_for']}'{c}':",
                        options=[STR["choose"]] + definicoes_baralhadas,
                        key=f"assoc_{idx}",
                    )

            if st.button(STR["btn_check_m2"], icon=":material/check_circle:", key="btn_valida_m2"):
                acertos = 0
                for idx, p in enumerate(pares):
                    d_user = respostas_assoc.get(idx, STR["choose"])
                    if d_user == STR["choose"]:
                        st.warning(f"{STR['assoc_no_answer']}'{p['conceito']}'.")
                    elif d_user == p["definicao"]:
                        acertos += 1
                        st.success(f"Correto: '{p['conceito']}' {STR['assoc_good']}")
                    else:
                        st.error(f"{STR['assoc_bad']}'{p['conceito']}'. {STR['assoc_hint']}")
                st.metric(STR["assoc_result"], f"{acertos}/{len(pares)} {STR['assoc_pairs_ok']}")

# ----------------------------------------------------------
# MÓDULO 3
# ----------------------------------------------------------
with tab3:
    st.header(STR["m3_header"])
    if offline:
        st.info(STR["m3_off_info"])
    else:
        st.markdown(STR["m3_on_desc"])

    if offline:
        # ---- Versão 100% utilizável sem chave ----
        pergunta_manual = st.text_input(STR["q_teacher_label"], key="m3_pergunta_manual")
        keywords = st.text_input(STR["kw_label"], placeholder=STR["kw_ph"], key="m3_kw")
        resposta_off = st.text_area(STR["answer_label"], height=100, key="m3_resp_off")
        if st.button(STR["btn_correct_off"], icon=":material/check_circle:", key="btn_m3_off"):
            if not pergunta_manual.strip():
                st.warning(STR["ask_question_first"])
            elif not keywords.strip():
                st.warning(STR["ask_kw_first"])
            elif not resposta_off.strip():
                st.warning(STR["ask_answer_first"])
            else:
                r = corrigir_por_keywords(resposta_off, keywords)
                st.divider()
                st.subheader(STR["report_off"])
                c1, c2 = st.columns(2)
                with c1:
                    if r["resultado"] == "CERTO":
                        st.markdown(f"<div class='correct-badge'>{STR['state_good']}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='incorrect-badge'>{STR['state_bad']}</div>", unsafe_allow_html=True)
                with c2:
                    st.metric(STR["score"], f"{r['nota_percentual']}%")
                st.markdown(f"**{STR['feedback_label']}** {r['feedback']}")
    elif is_student:
        # ---- Aluno: responde à pergunta e imagem já preparadas pelo professor ----
        if "pergunta_multimodal" in st.session_state and "img_bytes" in st.session_state:
            try:
                st.image(
                    Image.open(io.BytesIO(st.session_state["img_bytes"])),
                    caption=STR["img_caption"],
                    width=450,
                )
            except Exception:
                pass
            st.warning(f"**{STR['generated_q']}** {st.session_state['pergunta_multimodal']}")
            resposta_aluno = st.text_area(STR["answer_label"], height=100, key="m3_resp_student")
            if st.button(STR["btn_eval"], icon=":material/smart_toy:", key="btn_corrigir_student"):
                if resposta_aluno.strip():
                    with st.spinner(STR["spin_eval"]):
                        avaliar_resposta_aberta(
                            st.session_state["img_bytes"],
                            st.session_state["pergunta_multimodal"],
                            resposta_aluno,
                        )
                else:
                    st.warning(STR["need_answer"])
        else:
            st.info(STR["student_no_data"])
    else:
        uploaded_file = st.file_uploader(STR["upload_label"], type=["jpg", "jpeg", "png"])

        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file).convert("RGB")
            except Exception as e:
                st.error(f"{STR['img_open_err']}{e}")
                image = None

            if image is not None:
                # Guarda os bytes para a correção (e para o modo Aluno) e descarta
                # a pergunta anterior se a imagem mudou
                img_id = f"{uploaded_file.name}_{uploaded_file.size}"
                st.session_state["img_bytes"] = imagem_para_bytes(image)
                if st.session_state.get("_img_id") != img_id:
                    st.session_state.pop("pergunta_multimodal", None)
                    st.session_state["_img_id"] = img_id
                st.image(image, caption=STR["img_caption"], width=450)

                if st.button(STR["btn_gen_q"], icon=":material/auto_awesome:", key="btn_pergunta_img"):
                    with st.spinner(STR["spin_img"]):
                        try:
                            resposta_questao = client.models.generate_content(
                                model=model_name,
                                contents=[
                                    f"{INSTR} Analisa detalhadamente este suporte visual educativo e formula UMA pergunta analítica curta, direta e pedagógica que exija do aluno uma resposta aberta sucinta. / Analyse this educational visual and formulate ONE short analytical question requiring a brief open answer.",
                                    types.Part.from_bytes(
                                        data=st.session_state["img_bytes"], mime_type="image/png"
                                    ),
                                ],
                            )
                            pergunta_gerada = getattr(resposta_questao, "text", "") or ""
                            if not pergunta_gerada.strip():
                                st.error(STR["ia_no_question"])
                            else:
                                st.session_state["pergunta_multimodal"] = pergunta_gerada
                        except Exception as e:
                            dica = f" {STR['model_404_hint']}" if modelo_indisponivel(e) else ""
                            st.error(f"{STR['gen_q_err']}{e}{dica}")

                if "pergunta_multimodal" in st.session_state:
                    st.warning(f"**{STR['generated_q']}** {st.session_state['pergunta_multimodal']}")
                    resposta_aluno_aberta = st.text_area(STR["answer_label"], height=100, key="m3_resp_teacher")

                    if st.button(STR["btn_eval"], icon=":material/smart_toy:", key="btn_corrigir_aberta"):
                        if resposta_aluno_aberta.strip():
                            with st.spinner(STR["spin_eval"]):
                                avaliar_resposta_aberta(
                                    st.session_state["img_bytes"],
                                    st.session_state["pergunta_multimodal"],
                                    resposta_aluno_aberta,
                                )
                        else:
                            st.warning(STR["need_answer"])


# ----------------------------------------------------------
# STATUS BAR (decorative retro chrome)
# ----------------------------------------------------------
st.markdown(
    '<div class="mac-statusbar"><div>Ready <span class="cursor"></span></div><div>EduGen OS · Mem 640K</div></div>',
    unsafe_allow_html=True,
)
