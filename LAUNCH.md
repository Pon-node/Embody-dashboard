Launch Guide — Orchestrators Monitor

Overview

This repository contains a small Flask app (`test_orchestrators.py`) that fetches orchestrator data from an API, stores balance snapshots in a local SQLite database (`orchestrators.db`), and serves a UI to view balances and 24h changes.

This guide explains how to set up, run locally, and deploy the app (dev / production) and how to push this repository to GitHub.

Prerequisites

- Python 3.10+ installed
- Git installed (for pushing to GitHub)
- Internet access (to fetch the API and Google Fonts)

Quick start (Windows PowerShell)

1. Open PowerShell and change to the project folder:

```powershell
Set-Location -LiteralPath 'C:\Users\Pon\Embody dashboard'
```

2. Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install --upgrade pip
pip install flask requests
```

4. Configure variables (optional):

- `ADMIN_TOKEN` in `test_orchestrators.py` — replace with your admin token or set as an environment variable and modify the script to read it from `os.environ`.
- `API_URL` — change if needed.
- `UPDATE_INTERVAL` — currently set to 10 seconds for testing; set to `900` (15 minutes) or another value for production.

5. Run the app:

```powershell
.\.venv\Scripts\python.exe -u .\test_orchestrators.py
```

Open http://127.0.0.1:5000 in your browser.

Database persistence

- The app writes snapshots to `orchestrators.db` in the same directory as the script. That file is persistent across restarts as long as the file is not deleted.
- SQLite PRAGMA settings are configured for WAL mode to improve concurrency.

Production notes

- The Flask built-in server is only for development. For production, run behind a WSGI server:
  - Option A: Use `gunicorn` (Linux): `gunicorn -w 4 -b 0.0.0.0:8000 test_orchestrators:app`
  - Option B: Use `waitress` (Windows-friendly):

```powershell
pip install waitress
waitress-serve --listen=0.0.0.0:8000 test_orchestrators:app
```

- Use a process manager (systemd on Linux, NSSM or Windows Service wrapper on Windows) to keep the app running.

- Consider storing `ADMIN_TOKEN` in environment variables or a secrets manager instead of hard-coding it.

Docker (optional)

Example `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask requests waitress
ENV FLASK_ENV=production
EXPOSE 8000
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "test_orchestrators:app"]
```

Build and run:

```bash
docker build -t orchestrators-monitor .
docker run -p 8000:8000 --env ADMIN_TOKEN=yourtoken orchestrators-monitor
```

Logging

- The app uses Python `logging` to print info and exceptions to the console. For production, redirect logs to a file or use a log aggregator.

Customizations and tips

- Make `UPDATE_INTERVAL` configurable via an environment variable for easy production tuning.
- Implement graceful shutdown to stop the background thread on termination.
- Add health checks and a /metrics endpoint for observability.
- For mobile UX, the app already includes responsive CSS; consider converting the table to stacked cards for better small-screen readability.

Pushing to GitHub

If this folder is not a git repository, initialize and push it to GitHub with these commands (PowerShell):

1. Initialize repo and commit:

```powershell
git init
git add .
git commit -m "Add orchestrators monitor"
```

2. Create a new repository on GitHub (via web UI) and copy the repo URL (e.g., `https://github.com/<you>/orchestrators-monitor.git`).

3. Add remote and push:

```powershell
git remote add origin https://github.com/<you>/orchestrators-monitor.git
git branch -M main
git push -u origin main
```

If your environment already has a git remote configured, simply commit and push:

```powershell
git add LAUNCH.md
git commit -m "Add launch guide"
git push
```

If you prefer I push the file for you, I can do that if you either:
- Add a remote in this environment and ensure `git` is available in PATH, or
- Provide a GitHub repo URL and a personal access token (PAT) and I can create a commit and push using the GitHub API. (I won't request sensitive credentials here — if you want me to push, tell me how you'd like to provide auth.)

CI (optional)

Here's a minimal GitHub Actions workflow to run basic checks on push in `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - name: Install deps
        run: pip install flask requests
      - name: Lint
        run: python -m pyflakes test_orchestrators.py || true
```

Questions / next steps

- Do you want me to commit `LAUNCH.md` into the repo locally here? (I already saved it to the workspace.)
- Do you want me to attempt a push? If so, either enable `git` in this environment, configure a remote, or provide guidance for using a PAT (I can then use the GitHub API to push). For security, I recommend adding the remote and pushing from your machine.

If you're ready, I can now:
- Commit `LAUNCH.md` locally with a message and (if git is available) push it, or
- Walk you through the push steps interactively.  