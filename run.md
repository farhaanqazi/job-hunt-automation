# How to Run This App — Baby Steps

Super small steps. Do them in order. Each step is one thing.

---

## Part A — One-time setup (you only do this ONCE, ever)

> If you already set up the `.venv` folder before, skip to **Part B**.

### Step 1 — Open a terminal
- Press the **Windows key**.
- Type `powershell`.
- Click **Windows PowerShell**.

### Step 2 — Go into the project folder
Copy this line, paste it into PowerShell, press **Enter**:
```powershell
cd F:\job_hunt_automation
```

### Step 3 — Create the virtual environment
(A "virtual environment" is just a private box that holds this app's tools.)
```powershell
python -m venv .venv
```
Wait until you get your prompt back. Nothing prints. That's normal.

### Step 4 — Turn the virtual environment ON
```powershell
.\.venv\Scripts\Activate.ps1
```
You should now see `(.venv)` at the start of your prompt line. That means it worked.

> If you see a red error about "running scripts is disabled", run this once, then redo Step 4:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
> Type `Y` and press Enter if it asks.

### Step 5 — Install the app's tools
```powershell
pip install -e ".[dev]"
```
This downloads things. Wait for it to finish (it ends with `Successfully installed ...`).

**Setup is done.** You never have to do Part A again.

---

## Part B — Every time you want to use the app

### Step 1 — Open PowerShell and go to the folder
```powershell
cd F:\job_hunt_automation
```

### Step 2 — Turn the virtual environment ON
```powershell
.\.venv\Scripts\Activate.ps1
```
Look for `(.venv)` at the start of your prompt. If you see it, you're ready.

### Step 3 — See the list of job sources (a safe first test)
```powershell
python main.py sources list
```
You should see a table with remotive, adzuna, greenhouse, lever, arbeitnow.
If you see that table, **the app works.**

---

## Part C — Actually find jobs

### Step 1 — Download jobs from Remotive (no API key needed)
```powershell
python main.py scan --source remotive
```
It prints something like `Stored 30 jobs from remotive.`

### Step 2 — See the jobs it found
```powershell
python main.py jobs list --min-score 30
```
This shows a table: ID, score, remote type, company, title.

### Step 3 — Look at one job in detail
Pick an **ID** number from the table above, then (example uses `1`):
```powershell
python main.py jobs show 1
```

### Step 4 — Save a job to your shortlist
```powershell
python main.py jobs shortlist 1
```

### Step 5 — Export everything to a spreadsheet file
```powershell
python main.py export csv --output exports/jobs.csv
```
The file appears at `F:\job_hunt_automation\exports\jobs.csv`. Open it in Excel.

---

## Part D — (Optional) Turn on Adzuna for more jobs

Adzuna needs a free API key. Skip this if you just want Remotive.

### Step 1 — Make your settings file
```powershell
copy .env.example .env
```

### Step 2 — Open `.env` in Notepad
```powershell
notepad .env
```

### Step 3 — Paste your Adzuna keys
Find these two lines and put your keys after the `=` (no spaces, no quotes):
```
ADZUNA_APP_ID=your_id_here
ADZUNA_APP_KEY=your_key_here
```
Save the file (Ctrl+S) and close Notepad.
> Get free keys at https://developer.adzuna.com/ — this is the only place you enter them. Never paste keys into a chat.

### Step 4 — Scan Adzuna for India remote Python jobs
```powershell
python main.py scan --source adzuna --country in --query "python remote"
```

---

## Quick reference — all the commands

| What you want | Command |
|---|---|
| List sources | `python main.py sources list` |
| Check which sources are ready | `python main.py sources check` |
| Get jobs from Remotive | `python main.py scan --source remotive` |
| Get jobs from Adzuna | `python main.py scan --source adzuna --country in --query "python remote"` |
| Show found jobs | `python main.py jobs list --min-score 30` |
| Show one job | `python main.py jobs show <ID>` |
| Shortlist a job | `python main.py jobs shortlist <ID>` |
| Archive a job | `python main.py jobs archive <ID>` |
| Status summary | `python main.py tracker status` |
| Export to CSV | `python main.py export csv --output exports/jobs.csv` |
| See any command's help | add `--help`, e.g. `python main.py jobs --help` |

---

## If something breaks

- **`python` is not recognized** → Python isn't installed or not on PATH. Install Python 3.11+ from python.org and tick "Add to PATH".
- **No `(.venv)` in your prompt** → you skipped Part B, Step 2. Run `.\.venv\Scripts\Activate.ps1` again.
- **`ModuleNotFoundError`** → the tools aren't installed. Do Part A, Step 5: `pip install -e ".[dev]"`.
- **A red `FileNotFoundError` mentioning `cacert.pem` / `%VIRTUAL_ENV%`** → that was a broken machine setting. It has been fixed. Just **close PowerShell and open a fresh one**, then retry.
- **Anything else** → run the command again with `--help` on the end to see the right spelling.
