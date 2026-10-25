# Changelog

Todas as alterações notáveis deste projeto ficam documentadas neste ficheiro.

O formato é inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

Auditoria completa "à prova de bugs": revisão de todo o fluxo (offline + online,
editor, recuperação, histórico e exportações) com correções e testes de regressão.

### Corrigido

- **Submissão antiga sobrevivia ao editor** — adicionar pergunta/lacuna ou repor a
  base demo limpava as respostas mas não `m1_submetido`, e o painel de resultados
  reaparecia de imediato com erros falsos "Sem resposta". Os três gatilhos do editor
  invalidam agora a submissão anterior.
- **Opções duplicadas no quiz** — `ajustar_num_opcoes` unifica opções erradas iguais
  (ex. `["A","B","B","C"]`) antes de baralhar; perguntas assim deixam de ser
  rejeitadas como inválidas no render. O editor offline também rejeita opções
  duplicadas apenas por caixa/acento ("Frames" vs "frames").
- **Tema fiel na exportação e no histórico** — o recurso guarda o tema do momento
  da geração (`_tema`, nos geradores offline e no caminho Online) e um novo auxiliar
  `tema_de_recurso` dá prioridade a ele: exportar `.md`/`.pdf`, nomes de ficheiro e
  as linhas do histórico já não mudam de título quando o tema da barra lateral é
  editado depois de gerar.
- **PDF translitera acentos fora do cp1252** — `_cp1252` passa a tentar a
  decomposição NFKD (o acento cai, p. ex. "ř"→"r") antes de substituir por "?";
  carateres cp1252 e o em dash passam intactos, `π`/`∑` continuam "?".
- **Marca tolerante a `assets/` em falta** — `page_icon`/`st.logo` degradeam para um
  ícone material quando `assets/edugen_mark.png` não existe (o entregável é um
  ficheiro único; uma cópia só do `.py` não pode crashar no arranque).
- **Aviso de palavras-chave no papel Aluno (Módulo 3 offline)** — quando o professor
  não definiu palavras-chave, o Aluno passava a mensagem "Defina as palavras-chave
  esperadas", que só o Professor pode cumprir; agora recebe instrução para pedir ao
  professor (chave nova `ask_kw_student`, paridade PT/EN verificada).
- **Texto do editor sobrevivia à regeneração** — o `session_state` da textarea
  (`ed_texto`) sobrepõe-se ao `value=`: gerar um novo recurso (`btn_m1`) não limpava
  esse estado e "Guardar texto" reescrevia o texto **antigo** por cima do recurso
  novo. A regeneração limpa agora o editor de texto.

### Alterado

- Suíte alargada para 177 testes unitários (+12): dedupe de opções, transliteração
  NFKD do PDF, tema do recurso, editor stale e 6 verificações estáticas novas.
- **PDF em cache por assinatura** — o exportador renderiza em cada rerun; o PDF só
  se reconstrói quando o conteúdo muda (md5 do próprio `.md`), em vez de a cada
  interação com qualquer widget do Módulo 1.

## [1.0.0] — 2026-10-24

Primeira versão marcada: integra o trabalho de robustez, o redesign de identidade
visual e as melhorias pedagógicas Tier 2/3 descritas abaixo.

### Adicionado

- **Modo de recuperação (Módulos 1 e 2)** — após submeter com falhas, o botão
  "Praticar só o que falhei" cria um recurso de recuperação com apenas os itens errados
  (`dados_repetir_m1` / `dados_repetir_m2`), com banner explicativo e botão de saída;
  ao terminar no 100% o recurso completo volta automaticamente limpo.
- **Nível cognitivo (taxonomia de Bloom)** — seletor Recordar/Aplicar/Analisar no
  Módulo 1; a geração Online recebe o nível como item 4 do prompt, exigindo que
  enunciados, opções e explicações fiquem alinhados com o nível escolhido.
- **Bancos demo em inglês** — `BANCO_M1_*_EN`, `BANCO_M2_*_EN` e template genérico EN;
  os geradores offline passam a aceitar `lang="pt"|"en"` e os call sites usam o
  idioma da sessão (a antiga nota "banco em português" deixou de ser necessária).
- **Histórico da sessão (Professor)** — os gerados registam-se na barra lateral
  (máx. `MAX_HISTORICO = 5`, mais recente primeiro, snapshots copiados em profundidade)
  e podem ser repostos por um clique; o restauro limpa respostas e submissões pendentes.
- **Exportação em PDF (fpdf2)** — botão `.pdf` no exportador do Professor, a partir do
  mesmo Markdown do `.md`; sanitização cp1252 determinística (`_cp1252`) para subscritos
  (CO₂), setas (↔) e comparadores (≥); dependência tolerante a falhas (sem fpdf2 a app
  continua e não aparece o botão; um erro no PDF nunca derruba a aba).
- **`CHANGELOG.md`** e tag `v1.0.0` no repositório.
- Suíte alargada para 165 testes unitários (+33): modo de recuperação, bancos EN,
  histórico e PDF; smoke test end-to-end com fluxo 3b (entrar/sair do modo de
  recuperação) e verificação do botão PDF.

### Alterado

- **Identidade visual** — redesign Omarchy-inspired pelo autor: dark terminal
  (`#0f0f0f`), JetBrains Mono em tudo, acentos verdes (`#4ADE80`), scanlines, zero
  border-radius, hero em ASCII-art com titlebar de terminal.
- **Widgets com contratos estáveis** — sentinela `SELECAO_NULA` para os selectboxes do
  Módulo 2, papel/modo independentes do idioma e submissões (`m1_submetido`,
  `m2_submetido`) persistentes entre reruns.
- **Validações reforçadas** — perguntas exigem opções únicas e índice `int` não-bool;
  correção por palavras-chave respeita fronteiras de palavra.
- **Módulo 3 offline no papel Aluno** — mostra a pergunta já definida pelo professor
  (guardada em session_state) em vez de um estado vazio.

### Corrigido

- **Recuperação de dados corrompidos local à aba** (26d4a51) — o `st.stop()` a meio das
  abas matava os módulos restantes; agora cada módulo repara os próprios dados.
- **Piso do Streamlit alinhado com a UI** (26d4a51) — `streamlit>=1.51` reflete
  `linkColor`/`codeTextColor`; versus um piso antigo que degradava a identidade visual
  em silêncio.
- **Codificação e cursor do PDF** — as fontes core do fpdf2 são latin-1 por omissão
  (o em dash "—" partia a exportação): elevado para `windows-1252`; e o cursor do
  `multi_cell` (default `new_x=RIGHT` nesta versão) é agora explicitado para voltar
  à margem esquerda, senão as linhas seguintes ficam sem espaço horizontal.

## Sobre versões anteriores

O histórico fino vive nas mensagens de commit (`git log`); este ficheiro começa na
v1.0.0, que é a primeira autoridade de versão do projeto.
