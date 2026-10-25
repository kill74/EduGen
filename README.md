# EduGen — Gerador e Avaliador Educativo Inteligente

[![Testes](https://github.com/kill74/EduGen/actions/workflows/ci.yml/badge.svg)](https://github.com/kill74/EduGen/actions/workflows/ci.yml)

Aplicação web interativa, desenvolvida em Python com Streamlit, que gera recursos didáticos
a partir de um tema de aula (texto explicativo, questionário de escolha múltipla e exercícios
de preenchimento de lacunas), cria um jogo de associação de conceitos e avalia respostas de
alunos — tudo com apoio de inteligência artificial (Google Gemini) e com um **modo
Offline/Demo totalmente funcional, sem qualquer chave de API**.

**Demo aberta na nuvem**: [edugen-afts2gaappbcdvms8bapp2js.streamlit.app](https://edugen-afts2gaappbcdvms8bapp2js.streamlit.app/) — arranca em modo Offline/Demo, sem chave (sem tráfego a app adormece e acorda ao abrir).

## Contexto académico

Este projeto foi desenvolvido no âmbito da unidade curricular **DSI — Design de Sistemas
Interativos**. O enunciado pedia que o trabalho fosse realizado **recorrendo exclusivamente a
inteligência artificial**: a conceção, a implementação e a documentação resultaram de um
processo iterativo com modelos de IA generativa, com revisão e validação humana em cada passo.

O repositório reflete esse processo — inclui a aplicação, uma suite de 189 testes unitários
(sem dependências externas) e um smoke test end-to-end que exercita a aplicação real através
do *AppTest* do Streamlit (14 fluxos).

## Funcionalidades

| Módulo | Online (Gemini) | Offline / Demo (sem chave) |
|---|---|---|
| Conteúdo + Quiz + Lacunas | Geração por IA a partir do tema pedido | Bancos locais (ADN, Fotossíntese, Sistemas Operativos; PT e EN) + template genérico |
| Texto colado → quiz (Módulo 1) | Quiz e lacunas gerados por IA a partir do texto introduzido | Heurística local: termos do próprio texto, sem factos inventados |
| Jogo de associação conceito ↔ definição | 4 pares gerados por IA | Pares do banco local |
| Avaliação multimodal | Pergunta analítica sobre imagem + correção semântica por IA | Pergunta manual + correção por palavras-chave |

### Experiência de utilização

- **Papéis** — Professor (gera, edita e valida) e Aluno (responde sem ver as respostas antes
  de submeter); a troca de papel nunca perde o conteúdo já gerado.
- **Bilingue** — interface integral em Português e English, com paridade garantida por testes;
  os bancos demo também existem em inglês.
- **Nível cognitivo (Bloom)** — escolhe o nível das perguntas do quiz (Recordar, Aplicar,
  Analisar); a geração Online alinha enunciados, opções e explicações com o nível pedido.
- **Modo de recuperação** — ao submeter com falhas nos Módulos 1 e 2, o botão "Praticar só o
  que falhei" carrega um recurso apenas com os itens errados, com banner e saída em qualquer
  altura; a chegar ao 100%, o recurso completo volta automaticamente limpo.
- **Histórico da sessão (Professor)** — os últimos 5 recursos gerados ficam na barra lateral
  e podem ser repostos com um clique, sem perder o estado limpo das respostas.
- **Editor offline (Professor)** — editar o texto, adicionar ou remover perguntas e lacunas e
  repor a base demo; o estado sobrevive à mudança de módulo, de papel e de idioma.
- **Exportar/Imprimir (Professor)** — descarrega o recurso em Markdown e, com o fpdf2
  instalado, também em PDF (texto, quiz com chaves de resposta, lacunas e pares do jogo);
  a impressão direta (Ctrl+P) sai limpa, sem barra lateral.
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
- **Codificação do PDF à prova de falhas**: um erro na exportação PDF mostra um aviso e
  preserva o `.md`, em vez de derrubar a aba.

## Design e identidade visual

A interface segue uma direção de terminal/ASCII (inspirada no Omarchy), em vez de um
clichê de produtividade:

- **Paleta** — superfície terminal escura (`#0f0f0f`/`#1a1a1a`), texto cinzento quente
  (`#d4d4d4`) e acento verde (`#4ADE80`) para o ativo/selecionado; `#F87171` (vermelho) e
  `#FBBF24` (âmbar) reservados aos pontos de estado do hero.
- **Tipografia** — *JetBrains Mono* em tudo (texto, títulos e código), via `config.toml`.
- **Tema** — definido em `.streamlit/config.toml` (dark, raio de borda 0, sidebar mais
  clara); o que o tema não exprime vive numa folha CSS própria injetada via `st.html`
  (sem `unsafe_allow_html`).
- **Detalhes** — hero em ASCII-art com titlebar de terminal e badge de pulso, textura de
  scanlines, abas de terminal com indicador sublinhado, métricas em verde com luz CRT,
  glyphs `##`/`›` nos cabeçalhos do ecrã principal e respeito por `prefers-reduced-motion`.
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

## Roteiro de apresentação (5 minutos)

Ordem de demonstração testada — cada passo já foi apanhado pelo smoke:

1. **Arranque em modo Offline/Demo** (~20 s de pausa no hero): mostrar o banner
   "sem chave" e como a app funciona de imediato — este é o gancho da demo.
2. **Módulo 1**: gerar com o tema "A Fotossíntese", responder 1 pergunta certa e
   submeter — aparecem o resumo de estudo e a métrica real. Submeter sem responder
   para mostrar os avisos "Sem resposta" sem qualquer falha.
3. **Modo de recuperação**: no resumo, "Praticar só o que falhei" → banner de
   recuperação → resolver → sair para o recurso completo.
4. **Módulo 2**: criar o jogo, errar uma e validar — pares certos/errados, depois
   retry afunilando para a região do erro.
5. **Editor + exportação**: no editor alterar o texto ("Guardar texto"), depois
   "Exportar recurso" → abrir o `.md` **e** o `.pdf` gerados "fora da app".
6. **Trocar papél e idioma**: Professor→Aluno (a geração desaparece, o conteúdo
   fica), Português→English (a UI muda; chave e modelo não se perdem). Fecha a
   narrativa: robustez de contratos, não truque visual.

Extra (se sobrar tempo): na origem do Módulo 1, trocar para "A partir de texto colado", colar
um parágrafo de um manual e gerar — mostra a heurística local texto → lacunas/quiz, sem IA.

## Deploy na nuvem (Streamlit Community Cloud)

A aplicação é um ficheiro único, com dependências declaradas e arranque em modo
Offline/Demo — pode ser publicada na nuvem sem chaves e sem configuração.

1. Cria conta em [share.streamlit.io](https://share.streamlit.io/) com a tua conta GitHub.
2. Autoriza o acesso ao repositório (`kill74/EduGen`).
3. **Create app** → *from existing repo*: cola `kill74/EduGen`, branch `master`,
   ficheiro principal `TrabalhoPython.py`.
4. URL à escolha (neste repo: `edugen-afts2gaappbcdvms8bapp2js` — demo aberta acima) e Python **3.12** (o mesmo do CI) → **Deploy**.
5. (Opcional, para o modo Online) **Settings → Secrets** e cola:

```toml
GEMINI_API_KEY = "a-tua-chave"
```

Notas: a app publica sem qualquer segredo e o modo Offline funciona de imediato; a primeira
compilação demora 1-2 minutos (a Cloud instala as dependências do `requirements.txt`);
após inatividade a app adormece e o acesso seguinte reconstrói-a automaticamente.

## Website

A página de apresentação vive em [`docs/index.html`](docs/index.html) — um único ficheiro
HTML/CSS na linguagem visual da app (terminal, ASCII-art, zero `<script>`) e serve no
GitHub Pages em *Settings → Pages → Build from branch → `master` / `docs`*
([https://kill74.github.io/EduGen/](https://kill74.github.io/EduGen/), logo que ativado).

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
python -m unittest test_edugen -v    # 189 testes: lógica, strings, texto->quiz, estáticos, UI e quota
python smoke_fluxos.py               # 14 fluxos end-to-end sobre a aplicação real (AppTest)
```

Os testes correm também automaticamente no GitHub Actions (`.github/workflows/ci.yml`) a cada
push — o badge no topo do README mostra o último resultado.

A suite unitária usa apenas a biblioteca padrão e cobre a extração segura de JSON, a
normalização de texto, a correção por palavras-chave, a quota e o fallback de modelos,
os bancos demo PT/EN, o modo de recuperação, o histórico da sessão, a exportação
Markdown/PDF, a paridade PT/EN e regressões da interface. O smoke test percorre os
três módulos em modo offline, os dois papéis, os dois idiomas, o fluxo online sem
chave e a exportação.

## Estrutura do projeto

```text
TrabalhoPython.py        # aplicação Streamlit (lógica + interface)
test_edugen.py           # suite de testes unitários (só biblioteca padrão)
smoke_fluxos.py          # smoke test end-to-end (Streamlit AppTest)
docs/index.html          # website de apresentação (GitHub Pages, /docs)
.github/workflows/ci.yml # integração contínua: testes a cada push
.streamlit/config.toml   # tema: tipografia, paleta e barra lateral
.streamlit/secrets.toml.example # modelo para a chave API (modo Online)
CHANGELOG.md             # alterações notáveis por versão (Keep a Changelog)
LICENSE                  # MIT, com nota de uso académico
assets/edugen_mark.png   # marca da aplicação (logótipo e favicon)
requirements.txt         # dependências
```

## Decisões técnicas

- **Modo offline determinístico** — banco de exemplos local e simuladores de correção
  (escolha múltipla e palavras-chave), para que a demonstração nunca dependa da rede.
- **Resiliência a quotas** — fallback automático entre modelos, marcação de modelos esgotados
  e mensagens de erro acionáveis na interface.
- **PDF como dependência opcional** — com `fpdf2` instalado o exportador ganha um botão
  `.pdf`; sem ele a app corre normalmente e esconde o botão, e um erro do gerador nunca
  derruba a aba.
- **Ficheiro único deliberado** — a app e a suite de testes vivem num único
  `TrabalhoPython.py` (estrutura pedagógica do entregável): os testes isolam funções por
  fatias de código, pelo que não existe um pacote para partir.
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
reviewed by a human. The repository ships the application, 189 unit tests and a 14-flow
end-to-end smoke test. Recent additions include a Bloom-cognitive-level selector, a
"practice only what I missed" recovery mode, session history with one-click restore,
demo banks in English, PDF export (fpdf2) and a pasted-text mode that builds gap-filling
and multiple-choice exercises from the teacher's own class text.

---

Trabalho académico — DSI, 2026. Uso educativo.
