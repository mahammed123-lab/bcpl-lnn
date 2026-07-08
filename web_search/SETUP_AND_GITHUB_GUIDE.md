# JARVIS Web Search — Setup & GitHub Guide

Follow this top to bottom. Every command is copy-pasteable.

---

## Part 1 — Local Setup

### 1.1 Unzip the project
```bash
unzip web-search-multiLLM.zip
cd web-search
```

### 1.2 Create a virtual environment (keeps this project's packages separate from everything else on your machine)
```bash
python -m venv venv
```

Activate it:
- **Windows (cmd):** `venv\Scripts\activate.bat`
- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Mac/Linux:** `source venv/bin/activate`

You'll know it worked because your terminal prompt now starts with `(venv)`.

### 1.3 Install dependencies
```bash
pip install -r requirements.txt
```

### 1.4 Add your API key
```bash
cp .env.example .env
```
Open `.env` in any text editor. Find:
```
TAVILY_API_KEY=
```
Paste your key right after the `=`:
```
TAVILY_API_KEY=tvly-your-real-key-here
```
Save and close. Leave every other line blank — unused providers are skipped automatically.

### 1.5 Test it works
```bash
pytest -q
```
You should see something like `47 passed`. Then try a real search:
```bash
python -c "
from dotenv import load_dotenv
load_dotenv()
from web_search import SearchGate
import asyncio

gate = SearchGate.from_env()
result = gate.classify('latest NVIDIA GPU')
print(result)
if result.needs_search:
    data = asyncio.run(gate.search(result.search_query))
    print(data['direct_answer'])
"
```
If you see real search results printed, setup is done.

---

## Part 2 — Upload to GitHub

### 2.1 One-time git identity setup (skip if you've used git before)
```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### 2.2 Create the repo on GitHub (do this in your browser)
1. Go to https://github.com/new
2. Repository name: `web-search`
3. Visibility: **Private** (recommended — even though `.env` won't be uploaded, keep JARVIS-related code private if you like)
4. **Do NOT** check "Add a README" — you already have one. An empty repo is what you want here.
5. Click **Create repository**. Keep that page open — it shows the exact remote URL you'll need in step 2.5.

### 2.3 Double-check your real key won't be uploaded
```bash
cat .gitignore
```
Confirm `.env` is listed (it already is in this project). This is the file that keeps your real key local-only.

### 2.4 Initialize git and make your first commit
```bash
git init
git add .
git status
```
**Before committing**, read the `git status` output carefully — `.env` should **not** appear anywhere in the list. Only `.env.example` should show up. If you see `.env` listed, stop and fix `.gitignore` before continuing.

```bash
git commit -m "Initial commit: multi-provider search + multi-LLM gate"
git branch -M main
```

### 2.5 Connect to GitHub and push
Copy the URL GitHub showed you in step 2.2 (looks like `https://github.com/<username>/web-search.git`):
```bash
git remote add origin https://github.com/<your-username>/web-search.git
git push -u origin main
```
If prompted for a password, GitHub no longer accepts your account password directly — use a **Personal Access Token** instead:
1. https://github.com/settings/tokens → Generate new token (classic) → check the `repo` scope → Generate.
2. Copy the token and paste it as the password when git asks.
3. (Optional) Save it so you're not asked again: `git config --global credential.helper store` before pushing.

### 2.6 Confirm it worked
Refresh your GitHub repo page in the browser. You should see all the project files — and if you click into `.env.example`, it should show blank values. Search the repo for your actual key text just to be 100% sure it isn't anywhere:
```bash
git log --all -p | grep -i "tvly-"
```
This should return nothing.

---

## Part 3 — Making future changes

Every time you edit code and want to update GitHub:
```bash
git add .
git commit -m "describe what you changed"
git push
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `.env` shows up in `git status` | Run `git rm --cached .env` then re-check `git status` |
| Accidentally pushed a real key | Rotate/revoke the key immediately on the provider's dashboard first, then remove it from history with `git filter-repo` (rotating the key is the important step — it makes the leaked one useless) |
| `git push` asks for password and rejects it | Use a Personal Access Token instead of your GitHub password (see step 2.5) |
| `ModuleNotFoundError` when running Python | Make sure `(venv)` shows in your prompt — if not, re-run the activate command from step 1.2 |
| `pytest` fails | Run `pip install -r requirements.txt` again inside the activated venv |

---

## Quick reference — daily commands

```bash
# Activate environment (do this every time you open a new terminal)
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate.bat       # Windows

# Run tests
pytest -q

# Push changes to GitHub
git add .
git commit -m "message"
git push
```
