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
python -m unittest test_edugen -v   # 63 testes (lógica + estáticos)
```

Smoke test end-to-end da app real (requer dependências instaladas):

```bash
python /tmp/opencode/apptest_edugen.py   # 10 fluxos: papéis × idiomas × modos
```

## 🗂️ Estrutura

```
TrabalhoPython.py   # app Streamlit (lógica + UI)
test_edugen.py      # suite de testes (só biblioteca padrão)
requirements.txt    # dependências
```

## ⚙️ Modelos

`gemini-2.0-flash` (recomendado) · `gemini-2.5-flash` · `gemini-1.5-flash` · `gemini-1.5-pro`
