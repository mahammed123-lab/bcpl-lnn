# JARVIS Web Search

Multi-provider web search + multi-LLM answer synthesis, with automatic
fallback. Works with **one API key**.

## Quick Start

```bash
git clone https://github.com/<your-username>/web-search.git
cd web-search
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env`, add one key:

```bash
TAVILY_API_KEY=tvly-your-key-here
```

Run it:

```python
from dotenv import load_dotenv; load_dotenv()
from web_search import SearchGate
import asyncio

gate = SearchGate.from_env()
result = gate.classify("latest NVIDIA GPU")

if result.needs_search:
    data = asyncio.run(gate.search(result.search_query))
    print(data["direct_answer"])
```

That's it. No other config needed.

---

## Supported Providers

Set **any one** from each row — more keys just add parallel search +
automatic fallback, they're not required.

| Type | Providers | Env var |
|---|---|---|
| Search | Tavily, Serper, SerpAPI, SearXNG, NewsData | `TAVILY_API_KEY`, `SERPER_API_KEY`, `SERPAPI_API_KEY`, `SEARXNG_URL`, `NEWSDATA_API_KEY` |
| LLM | NVIDIA, Groq, OpenRouter, Together, Gemini, Ollama (local) | `NVIDIA_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `TOGETHER_API_KEY`, `GEMINI_API_KEY`, `OLLAMA_BASE_URL` |

Full list with descriptions → [`.env.example`](.env.example)

## What happens with 1 key vs. more

| You set | You get |
|---|---|
| 1 search key only | Real search, regex-based routing, provider's own quick answer. No AI-written summary. |
| 1 search key + 1 LLM key | Full pipeline: search-necessity classification, multi-source search, AI-synthesized cited answer. |
| Multiple search keys | Queries run in parallel across all of them, results merged & deduped, ranked by source trust. |
| Multiple LLM keys | If the first one fails or rate-limits, it automatically falls through to the next — no code change needed. |

## Project Structure

```
web_search/
├── classifiers/     # regex + LLM "does this need a search?" logic
├── providers/        # one file per search/LLM provider
│   └── llm/           # NVIDIA, Groq, OpenRouter, Together, Gemini, Ollama
├── engine/            # orchestrator, synthesizer, session, query expansion
├── config.py          # reads all env vars, one place to check what's configured
└── types.py           # shared dataclasses/enums
```

## Commands

```bash
pytest -q                 # run tests
gate.provider_status()    # check which providers are live vs. in cooldown
```

## Deploy checklist

- [ ] `.env` filled in locally, never committed (`.gitignore` already covers it)
- [ ] `pytest -q` passes
- [ ] `git status` doesn't show `.env` before your first commit
- [ ] Push: `git add . && git commit -m "init" && git push -u origin main`

Full step-by-step (including first-time GitHub account/repo setup) →
[`SETUP_AND_GITHUB_GUIDE.md`](SETUP_AND_GITHUB_GUIDE.md)
