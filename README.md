# Web Search (v7.1)

A standalone multi-provider web search + multi-LLM synthesis pipeline.

```
                  ┌──────────────────────┐
                  │     User Query       │
                  └──────────┬───────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │  Explicit `backtick` check│ ──► [True] ──► Force Search
               └─────────────┬─────────────┘
                             │ [False]
                             ▼
               ┌───────────────────────────┐
               │    Layer 1: Regex Match   │ ──► [High Conf] ──► Return Decision
               └─────────────┬─────────────┘
                             │ [Med/Low Conf]
                             ▼
               ┌───────────────────────────┐
               │     Layer 2: LLM Gate     │ ──► Return Decision
               └───────────────────────────┘
                             │
                             ▼  (needs_search == True)
               ┌───────────────────────────┐
               │  Multi-Provider Search    │  Tavily / Serper / SerpAPI /
               │  (circuit-broken router)  │  SearXNG / NewsData — in parallel
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │   Multi-LLM Synthesis     │  NVIDIA / Groq / OpenRouter /
               │  (circuit-broken router)  │  Together / Gemini / Ollama
               └───────────────────────────┘
```

## Features

- **Multi-Provider Search**: Circuit-broken routing across Tavily, SerpAPI, Serper, SearXNG, and NewsData.
- **Multi-Provider LLM (any single key works)**: Circuit-broken routing across NVIDIA NIM, Groq, OpenRouter, Together AI, Google Gemini, and a local Ollama instance. Both the search-necessity classifier and the answer synthesizer use the same router — set **one** LLM key and everything works end to end. If that provider errors out or rate-limits, the router automatically falls through to the next configured provider.
- **Three-Layer Classification**: Fast regex pre-checks trigger first to filter out conversational queries or obvious commands, handing off to LLM classification only for ambiguous queries.
- **Synthesized Answers**: Search results parsed, cleaned, and synthesized into a grounded, cited answer.
- **Stale Data Mitigation**: Knowledge cutoff prompt guidelines coupled with dynamic today's date injection.
- **Circuit breaker everywhere**: any provider (search or LLM) that fails `WEBSEARCH_FAILURE_THRESHOLD` times in a row is put on cooldown for `WEBSEARCH_COOLDOWN_SECONDS`, so a dead/rate-limited key doesn't eat a timeout on every single query.

## How "any single API key" works

You don't need every provider. Each provider file checks its own key and
silently returns "no result" if it's missing — the router just skips it.

- **Search**: configure *any one* of `TAVILY_API_KEY`, `SERPER_API_KEY`,
  `SERPAPI_API_KEY`, `SEARXNG_URL`, `NEWSDATA_API_KEY` and multi-provider
  search works (with only one provider running, obviously — add more
  keys later for parallel search + automatic fallback).
- **LLM / answers**: configure *any one* of `NVIDIA_API_KEY`,
  `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `TOGETHER_API_KEY`,
  `GEMINI_API_KEY`, or point `OLLAMA_BASE_URL` at a local Ollama server.
  That single key powers both the "does this need a web search?"
  classifier and the final answer synthesis.
- **Minimum working setup**: one search key + one LLM key. Everything
  else is optional redundancy.

Free tiers that work well for a minimum setup: **Tavily** (1,000
searches/month free) for search, and **Groq** (fast, generous free
tier) or **Gemini** (free tier) for the LLM side.

## Installation

```bash
git clone https://github.com/<your-username>/web-search.git
cd web-search
pip install -r requirements.txt
cp .env.example .env
# edit .env and fill in the keys you actually have
```

If you want `.env` to load automatically instead of exporting vars by
hand, install `python-dotenv` and add this before you import
`web_search` anywhere in your app:

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()

from web_search import SearchGate
gate = SearchGate.from_env()
```

## Environment Variables

See `.env.example` for the full, commented list. Summary:

| Category | Variable | Notes |
|---|---|---|
| Search | `TAVILY_API_KEY` | includes a direct-answer field |
| Search | `SERPER_API_KEY` | Google results via serper.dev |
| Search | `SERPAPI_API_KEY` | Google results via SerpAPI |
| Search | `SEARXNG_URL` | self-hosted or public instance, no key needed |
| Search | `NEWSDATA_API_KEY` | news-specific results |
| LLM | `NVIDIA_API_KEY` | NVIDIA NIM chat completions |
| LLM | `GROQ_API_KEY` | Groq — very low latency |
| LLM | `OPENROUTER_API_KEY` | routes to many free/paid models |
| LLM | `TOGETHER_API_KEY` | Together AI |
| LLM | `GEMINI_API_KEY` | Google Gemini |
| LLM | `OLLAMA_BASE_URL` | local Ollama, e.g. `http://localhost:11434`, no key |
| Tuning | `LLM_PROVIDER_PRIORITY` | comma-separated fallback order |
| Tuning | `WEBSEARCH_FAILURE_THRESHOLD` / `WEBSEARCH_COOLDOWN_SECONDS` | circuit breaker |

## Usage

```python
from web_search import SearchGate

# Initialize from system environment variables.
# call_llm is optional — if you don't pass one, SearchGate builds a
# default that routes across every configured LLM provider for you.
gate = SearchGate.from_env()

# Classify search-necessity
result = gate.classify("What's the latest NVIDIA GPU?")
if result.needs_search:
    import asyncio
    search_data = asyncio.run(gate.search(result.search_query))
    print(search_data["summary"])

# Check provider health (search + LLM) any time
print(gate.provider_status())
```

To plug in your own model instead of the built-in multi-LLM router
(e.g. your own orchestrator/brain module), just pass `call_llm`:

```python
gate = SearchGate.from_env(call_llm=my_own_llm_function)
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

---

## Uploading this project to GitHub

1. **Create the repo on GitHub** (web UI): New repository → name it
   `web-search` → keep it **Private** if it'll ever contain
   real keys in local config → don't initialize with a README (you
   already have one).

2. **Never commit real keys.** `.gitignore` already excludes `.env`
   and `*.env`. Double-check before your first commit:
   ```bash
   git status
   ```
   `.env` should NOT appear in the list of files to be committed —
   only `.env.example` (which has empty values) should.

3. **Initialize and push:**
   ```bash
   cd web-search
   git init
   git add .
   git commit -m "Multi-provider search + multi-LLM synthesis gate"
   git branch -M main
   git remote add origin https://github.com/<your-username>/web-search.git
   git push -u origin main
   ```

4. **If you ever accidentally commit a real key:** rotate/revoke that
   key immediately at the provider's dashboard, then remove it from
   git history (`git filter-repo` or GitHub's secret-scanning alert
   will point you to the commit). Rotating the key is the important
   part — history rewriting is cleanup, not the fix.

5. **Optional but recommended:**
   - Add a repo description + topics (`python`, `llm`, `search`, `web-search`).
   - Enable GitHub's secret scanning (Settings → Code security) so any
     future key you paste in by mistake gets flagged automatically.
   - If this will be imported into your main project repo as a
     submodule/dependency instead of standalone, use:
     ```bash
     git submodule add https://github.com/<your-username>/web-search.git your_project/search_gate
     ```
