# Job Search Agent

Multi-platform job-search assistant for Java/backend roles.

## Setup

```bash
cp .env.example .env
npm install
```

Add `APIFY_TOKEN` in `.env` if you want actor-backed searches.

## Configure

Edit `config/jobs.config.json`.

- Put Apify actor IDs in `platforms[].actorId` when you have a platform-specific actor.
- Leave `actorId: null` to use web-search fallback.
- Salary, date, experience, title rejection, and keyword filters live under `filters`.

## Run

```bash
npm run search
npm run review
npm run report
```

Outputs:

- `data/raw-jobs.json`
- `data/scored-jobs.json`
- `data/reviewed-jobs.json`
- `reports/latest.md`

No auto-apply is included. Review gate first.
