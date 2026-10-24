# Local Docs RAG Assistant

A local-first **retrieval-augmented generation (RAG)** assistant that answers questions about your own documents (PDF, DOCX, PPTX). It combines **hybrid retrieval** (semantic vectors + BM25 keywords) with a **Groq-hosted LLM**, streams answers token by token to a browser UI, and keeps your conversations in a local SQLite database.

Built for Turkish and multilingual documents, using a multilingual embedding model and Turkish-aware prompts.

<!-- Add a screenshot after your first run: docs/screenshot.png -->
<!-- ![Web UI](docs/screenshot.png) -->

## Features

- **Hybrid retrieval**: semantic search (65%) and BM25 keyword search (35%) merged into a single ranking, so both meaning and exact terms (names, numbers, codes) are matched.
- **Multilingual embeddings** with `intfloat/multilingual-e5-small`, running locally on CPU.
- **Streaming answers** over Server-Sent Events (SSE) with a live typing effect.
- **Grounded answers with page references**: retrieved chunks are labeled with their source page. When the document does not contain the answer, the assistant says so explicitly before falling back to the model's general knowledge.
- **Resilient LLM layer**: automatic fallback to backup models if the selected model is unavailable or rate-limited, and the UI is notified when a switch happens.
- **Persistent chat history** in SQLite, so past conversations survive restarts.
- **Local document picker**: choose a document in the UI and start chatting.
- **Fully configurable models**: no model is hard-wired. See [Choosing LLM models](#choosing-llm-models).

## How it works

```
Documents (PDF / DOCX / PPTX)
        |  load, clean, split into overlapping chunks
        v
Embeddings (multilingual-e5-small)  -->  Chroma vector store (cached on disk)
        |                                         |
        +--------  BM25 keyword index  -----------+
                                                  v
Question --> Hybrid retrieval: semantic top-10 + BM25 top-10
             --> weighted merge (0.65 / 0.35) --> top-4 chunks
                                                  v
          Prompt builder (chunks + chat history) --> Groq LLM (streaming, model fallback)
                                                  v
                     FastAPI + SSE --> Web UI        SQLite chat history
```

## Tech stack

| Area | Technology |
|---|---|
| API / server | FastAPI, Uvicorn, Server-Sent Events |
| LLM | Groq API (`groq` SDK) |
| Embeddings | `sentence-transformers`, `langchain-huggingface` (`intfloat/multilingual-e5-small`) |
| Vector store | Chroma via `langchain-chroma` |
| Keyword search | `rank-bm25` |
| Document loading | `pypdf`, `python-docx`, `python-pptx` |
| Persistence | SQLite |
| Frontend | Static HTML / CSS / JavaScript |

## Quick start

**Prerequisites:** Python 3.10+ (developed on 3.12) and a free [Groq API key](https://console.groq.com/keys).

```bash
git clone https://github.com/HasretIrmak/local-docs-rag-assistant.git
cd local-docs-rag-assistant

python -m venv .venv
source .venv/bin/activate        # Windows (Git Bash): source .venv/Scripts/activate

pip install -r requirements.txt

cp .env.example .env             # then put your Groq API key into .env
python main.py
```

`python main.py` starts the server and opens `http://127.0.0.1:8000` in your browser. The embedding model is downloaded from Hugging Face on the first run, so the first start takes longer.

## Configuration

Settings are read from environment variables or from a local `.env` file (git-ignored). Real environment variables take precedence over `.env`.

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | none (required) | Your Groq API key. |
| `RAG_GROQ_MODEL` | `qwen/qwen3.6-27b` | Primary model. |
| `RAG_FALLBACK_MODELS` | `openai/gpt-oss-120b,openai/gpt-oss-20b` | Comma-separated backup models, tried in order. |
| `SEARXNG_URL` | `https://searx.be` | Preferred SearXNG instance (see `config.py`). |
| `RAG_DEBUG` | `0` | Set to `1` for verbose logging. |
| `RAG_SHOW_CHUNKS` | `1` | Set to `0` to hide retrieved chunks in the UI. |

Retrieval parameters (chunk size and overlap, top-k values, score weights, thresholds) live in [`config.py`](config.py).

## Choosing LLM models

Hosted model catalogs change frequently: providers deprecate models and replace them with new ones. For that reason, **no model is hard-coded**. If you see a "model not found" or "decommissioned" error, or simply want a different model:

1. Check which models are currently available to your key at <https://console.groq.com/docs/models> (or call `https://api.groq.com/openai/v1/models`).
2. Set them in your `.env`:

   ```bash
   RAG_GROQ_MODEL=<primary-model-id>
   RAG_FALLBACK_MODELS=<backup-model-id-1>,<backup-model-id-2>
   ```

3. Restart the app.

Models in `RAG_FALLBACK_MODELS` are tried in order when the primary model fails. Use chat-capable text models only (not guard, speech, or embedding models).

## Project structure

```
.
├── main.py            # Entry point: starts the server and opens the browser
├── server.py          # FastAPI app and SSE streaming endpoints
├── config.py          # Settings, model chain, retrieval parameters
├── llm.py             # Groq client, prompts, streaming with model fallback
├── retrieval.py       # Hybrid retrieval (semantic + BM25)
├── embeddings.py      # Embedding model and vector store
├── preprocessing.py   # Document loading and chunking
├── memory.py          # Conversation memory
├── database.py        # SQLite chat history
├── utils.py           # Text helpers
├── static/            # Web UI (index.html, app.js, style.css)
├── requirements.txt
└── .env.example
```

## Privacy

Documents, embeddings, the vector store, and chat history stay on your machine. When you ask a question, the question, the retrieved text chunks, and recent chat history are sent to the Groq API to generate the answer.

## Limitations

- Designed as a single-user local tool: the server has no authentication and should not be exposed to the public internet as is.
- System prompts and intent triggers are written in Turkish; answers in other languages work but are less tuned.
- Answer quality depends on the chosen model and on how well the document text can be extracted (scanned PDFs without OCR will not work).

## Roadmap

- [ ] Automated tests and CI
- [ ] Docker image
- [ ] Source citations shown inline in the UI
- [ ] English localization of the UI and prompts
