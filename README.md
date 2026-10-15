# 🎓 EduGen — Gerador e Avaliador Educativo Inteligente

Plataforma interativa (Streamlit) para criação automática de recursos didáticos e avaliação
assistida por IA (Google Gemini), com **modo Offline/Demo que funciona sem chave API**.

Trabalho académico — DSI (Design de Sistemas Interativos).

## ✨ Funcionalidades

| Módulo | Online (Gemini) | Offline / Demo (sem chave) |
|---|---|---|
| 📚 Conteúdo + Quiz + Lacunas | Geração por IA do tema pedido | Banco local (ADN, Sistemas Operativos) + template genérico |
| 🧩 Jogo de associação conceito ↔ definição | 4 pares gerados por IA | Pares do banco local |
| 🖼️ Avaliação multimodal | Pergunta analítica sobre imagem + correção semântica por IA | Pergunta manual + correção por palavras-chave |

**UX:**
- 👩‍🏫/🧑‍🎓 Papéis **Professor** (gera, edita) e **Aluno** (responde sem ver respostas antes de submeter).
- 🌍 Interface em **Português / English** (seletor na barra lateral).
- ✏️ **Editor offline** (Professor): editar texto, adicionar perguntas e lacunas, repor demo.
- ✨ Interface **clean e minimal**: só componentes nativos do Streamlit, sem CSS custom.
- 🧭 **Resumo de estudo automático**: quando há erros (quiz, lacunas, jogo ou resposta aberta),
  a app mostra um pequeno resumo com a resposta certa, a explicação de cada falha e o que rever —
  funciona também offline.

## 🚀 Como correr

```bash
pip install -r requirements.txt
streamlit run TrabalhoPython.py
```

Abre `http://localhost:8501`. Na barra lateral escolhe:
- 📴 **Offline / Demo** — funciona logo, sem chave (ideal para demonstração).
- 🌐 **Online** — insere a chave do [Google AI Studio](https://aistudio.google.com/),
  ou define `GEMINI_API_KEY` nos Secrets/ambiente.

## ✅ Testes

```bash
python -m unittest test_edugen -v   # 118 testes (lógica + estáticos + UI + quota)
```

Smoke test end-to-end da app real (requer dependências instaladas):

```bash
python /tmp/opencode/apptest_edugen.py   # 14 fluxos: papéis × idiomas × modos + resumos de estudo
```

## 🗂️ Estrutura

```
TrabalhoPython.py   # app Streamlit (lógica + UI)
test_edugen.py      # suite de testes (só biblioteca padrão)
requirements.txt    # dependências
```

## ⚙️ Modelos

A lista de modelos é obtida automaticamente da tua chave API (nunca fica desatualizada).
Os recomendados para o tier gratuito aparecem primeiro; Pro/preview vão para o fim
(não têm quota gratuita). Recomendados: `gemini-3.8-flash` (mais recente) ·
`gemini-3.5-flash-lite` (muito económico) · `gemini-3.6-flash` · `gemini-3.1-flash-lite` ·
`gemini-2.5-flash-lite` · `gemini-2.5-flash` (chaves antigas).
Os nomes `gemini-1.5-*` e `gemini-2.0-*` foram desligados pela Google e já não existem na API.

**Escolha automática (padrão):** em cada geração a app usa o modelo gratuito **com menos
uso na sessão** (começa no `gemini-3.8-flash`) e distribui o trabalho pelos restantes
Flash à medida que vão sendo usados. Podes fixar um modelo concreto na barra lateral.

**Quota esgotada (429)?** A app reage sozinha: marca o modelo como cheio, passa ao
próximo menos usado e avisa-te — sem perder a geração em curso.
