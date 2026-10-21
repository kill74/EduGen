# EduGen — Gerador e Avaliador Educativo Inteligente

[![Testes](https://github.com/kill74/EduGen/actions/workflows/ci.yml/badge.svg)](https://github.com/kill74/EduGen/actions/workflows/ci.yml)

Aplicação web interativa, desenvolvida em Python com Streamlit, que gera recursos didáticos
a partir de um tema de aula (texto explicativo, questionário de escolha múltipla e exercícios
de preenchimento de lacunas), cria um jogo de associação de conceitos e avalia respostas de
alunos — tudo com apoio de inteligência artificial (Google Gemini) e com um **modo
Offline/Demo totalmente funcional, sem qualquer chave de API**.

## Contexto académico

Este projeto foi desenvolvido no âmbito da unidade curricular **DSI — Design de Sistemas
Interativos**. O enunciado pedia que o trabalho fosse realizado **recorrendo exclusivamente a
inteligência artificial**: a conceção, a implementação e a documentação resultaram de um
processo iterativo com modelos de IA generativa, com revisão e validação humana em cada passo.

O repositório reflete esse processo — inclui a aplicação, uma suite de 130 testes unitários
(sem dependências externas) e um smoke test end-to-end que exercita a aplicação real através
do *AppTest* do Streamlit (12 fluxos).

## Funcionalidades

| Módulo | Online (Gemini) | Offline / Demo (sem chave) |
|---|---|---|
| Conteúdo + Quiz + Lacunas | Geração por IA a partir do tema pedido | Bancos locais (ADN, Fotossíntese, Sistemas Operativos) + template genérico |
| Jogo de associação conceito ↔ definição | 4 pares gerados por IA | Pares do banco local |
| Avaliação multimodal | Pergunta analítica sobre imagem + correção semântica por IA | Pergunta manual + correção por palavras-chave |

### Experiência de utilização

- **Papéis** — Professor (gera, edita e valida) e Aluno (responde sem ver as respostas antes
  de submeter); a troca de papel nunca perde o conteúdo já gerado.
- **Bilingue** — interface integral em Português e English, com paridade garantida por testes.
- **Editor offline (Professor)** — editar o texto, adicionar ou remover perguntas e lacunas e
  repor a base demo; o estado sobrevive à mudança de módulo, de papel e de idioma.
- **Exportar/Imprimir (Professor)** — descarrega o recurso em Markdown (texto, quiz com
  chaves de resposta, lacunas e pares do jogo) para arquivar ou converter em PDF; a impressão
  direta (Ctrl+P) sai limpa, sem barra lateral.
- **Resumo de estudo automático** — quando há erros (quiz, lacunas, jogo de associação ou
  resposta aberta), a aplicação mostra a resposta certa, a explicação de cada falha e o que
  rever; funciona igualmente offline.
- **Celebração a 100%** — pontuação perfeita desencadeia balões e uma notificação.

### Robustez do modo online

- A lista de modelos é obtida da própria chave API, pelo que nunca fica desatualizada.
- **Escolha automática**: cada geração usa o modelo gratuito **com menos uso na sessão**;
  também é possível fixar um modelo concreto na barra lateral.
- **Quota esgotada (429)**: a aplicação marca o modelo como cheio, passa ao seguinte menos
  usado e avisa — sem perder a geração em curso.
- **Extração segura de JSON**: as respostas da IA são validadas antes de alimentar a
  interface; conteúdo malformado nunca bloqueia a aplicação.

## Design e identidade visual

A interface segue uma direção editorial própria, em vez do registo habitual de produtividade:

- **Paleta** — papel quente (`#FBF9F6`), tinta (`#23201C`), violeta profundo (`#5B21B6`) e um
  acento terracota (`#D97757`) usado com parcimónia.
- **Tipografia** — *Fraunces* (serifa expressiva) nos títulos, *Manrope* no texto corrente e
  *JetBrains Mono* no código.
- **Tema** — definido em `.streamlit/config.toml`, incluindo a barra lateral em tinta profunda;
  o que o tema não exprime vive numa folha CSS própria injetada via `st.html` (sem
  `unsafe_allow_html`).
- **Detalhes** — cabeçalho hero com retícula fina e brilho à deriva, abas em pílula, cartões
  com número em serifa, micro-interações discretas e respeito por `prefers-reduced-motion`.
- **Marca** — `assets/edugen_mark.png`, gerada localmente e usada como logótipo e favicon.

## Como executar

Requisitos: Python 3.10 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run TrabalhoPython.py
```

A aplicação abre em `http://localhost:8501`. Na barra lateral:

- **Offline / Demo** (predefinido) — funciona de imediato, sem chave (ideal para demonstração).
- **Online** — requer uma chave do [Google AI Studio](https://aistudio.google.com/), que pode
  ser introduzida na barra lateral, em `.streamlit/secrets.toml`
  (`GEMINI_API_KEY = "..."`) ou na variável de ambiente `GEMINI_API_KEY`.

## Modelos e quota

Os modelos recomendados para o tier gratuito aparecem primeiro; modelos Pro/preview vão para
o fim da lista, por não terem quota gratuita. Recomendados: `gemini-3.8-flash` (mais recente),
`gemini-3.5-flash-lite` (muito económico), `gemini-3.6-flash`, `gemini-3.1-flash-lite`,
`gemini-2.5-flash-lite` e `gemini-2.5-flash` (chaves antigas). Os nomes `gemini-1.5-*` e
`gemini-2.0-*` foram descontinuados pela Google e já não existem na API.

A opção **Automático** (predefinida) usa o modelo gratuito com menos uso na sessão e distribui
o trabalho pelos restantes à medida que vão sendo usados.

## Testes

```bash
python -m unittest test_edugen -v    # 130 testes: lógica, strings, estáticos, UI e quota
python smoke_fluxos.py               # 12 fluxos end-to-end sobre a aplicação real (AppTest)
```

Os testes correm também automaticamente no GitHub Actions (`.github/workflows/ci.yml`) a cada
push — o badge no topo do README mostra o último resultado.

A suite unitária usa apenas a biblioteca padrão e cobre a extração segura de JSON, a
normalização de texto, a correção por palavras-chave, a quota e o fallback de modelos, a
paridade PT/EN, a integração dos widgets e regressões da interface. O smoke test percorre os
três módulos em modo offline, os dois papéis, os dois idiomas e o fluxo online sem chave.

## Estrutura do projeto

```text
TrabalhoPython.py        # aplicação Streamlit (lógica + interface)
test_edugen.py           # suite de testes unitários (só biblioteca padrão)
smoke_fluxos.py          # smoke test end-to-end (Streamlit AppTest)
.github/workflows/ci.yml # integração contínua: testes a cada push
.streamlit/config.toml   # tema: tipografia, paleta e barra lateral
.streamlit/secrets.toml.example # modelo para a chave API (modo Online)
LICENSE                  # MIT, com nota de uso académico
assets/edugen_mark.png   # marca da aplicação (logótipo e favicon)
requirements.txt         # dependências
```

## Decisões técnicas

- **Modo offline determinístico** — banco de exemplos local e simuladores de correção
  (escolha múltipla e palavras-chave), para que a demonstração nunca dependa da rede.
- **Resiliência a quotas** — fallback automático entre modelos, marcação de modelos esgotados
  e mensagens de erro acionáveis na interface.
- **Privacidade e simplicidade** — a folha de estilo não carrega recursos externos; apenas as
  fontes declaradas no `config.toml` são obtidas via Google Fonts.
- **Paridade PT/EN verificada por testes** — todas as chaves de texto existem nos dois idiomas
  e nenhuma fica órfã.

## English summary

EduGen is an interactive Streamlit application that generates classroom resources and grades
student answers with Google Gemini, including a fully functional Offline/Demo mode that needs
no API key. It was developed for the **DSI — Design of Interactive Systems** course, under a
brief that required the project to be built **exclusively with artificial intelligence**:
conception, code and documentation were produced iteratively with generative AI models and
reviewed by a human. The repository ships the application, 130 unit tests and a 12-flow
end-to-end smoke test.

---

Trabalho académico — DSI, 2026. Uso educativo.
