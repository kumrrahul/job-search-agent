# Naukri Job Application Agent

Phase 1 MVP pipeline:

1. Scrape Naukri jobs from configured role aliases.
2. Extract matching keywords from each job description.
3. Tailor a LaTeX resume copy in `tmp/`.
4. Apply through Selenium.
5. Email an application summary.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with Naukri and SMTP credentials.

## Run

```bash
python run.py --dry-run --limit 2
python run.py --limit 5
python run.py --no-email
```

`pdflatex` must be installed and available on `PATH` for resume PDF generation. On macOS, BasicTeX is enough:

```bash
brew install --cask basictex
eval "$(/usr/libexec/path_helper)"
```

The resume generator checks `resume.preferred_pages: 1` from `config.yaml`. If a tailored PDF becomes two pages, the agent still applies and includes a resume page warning in the email summary.
