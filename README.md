# Job Search Agent

Multi-platform job-search assistant for Java/backend roles.

## What It Does

This project searches job boards, filters jobs against a resume and config, scores matches, and creates a Markdown report.

It does not auto-apply or message recruiters. Human review stays in the loop.

Flow:

1. Read resume PDF.
2. Extract resume skills and best-fit titles.
3. Search configured platforms.
4. Normalize job data into one format.
5. Deduplicate by company + title + location.
6. Reject poor fits using strict filters.
7. Score remaining jobs against resume skills.
8. Generate report and recruiter message templates.

## Setup From Scratch

```bash
cd /path/to/job-search-agent
cp .env.example .env
npm install
```

Add your Apify key in `.env`:

```env
APIFY_TOKEN=apify_api_your_token_here
```

Apify is optional for public/direct sources, but recommended for Indeed, Glassdoor, Naukri, Wellfound, and similar boards.

See `APIFY_SETUP.md` for Apify-specific steps.

## Configure For Your Resume

Edit `config/jobs.config.json`.

Set resume path:

```json
"resumePath": "/absolute/path/to/resume.pdf"
```

Set experience range:

```json
"filters": {
  "postedWithinDays": 7,
  "minExperience": 4,
  "maxExperience": 6
}
```

Set target job titles:

```json
"targetTitles": [
  "Java Developer",
  "Backend Developer",
  "Spring Boot Developer"
]
```

Set search keywords:

```json
"keywords": [
  "\"Java Developer\" \"Spring Boot\" \"4-6 years\"",
  "\"Backend Developer\" Java \"Spring Boot\" Microservices"
]
```

Set reject rules:

```json
"rejectTitleTerms": ["intern", "fresher", "manager", "architect", "lead"],
"rejectExperiencePatterns": ["0-1", "0-2", "0-3", "7+", "8+", "10+"]
```

## Configure Platforms

Each platform entry looks like:

```json
{
  "name": "Indeed",
  "domain": "indeed.com",
  "actorId": "valig/indeed-jobs-scraper",
  "actorInputType": "indeed-valig",
  "enabled": true
}
```

Rules:

- `enabled: true` searches platform.
- `enabled: false` skips platform.
- `actorId: null` uses direct API/RSS/web-search fallback.
- `actorId: "..."` uses Apify.
- Some actors need `actorInputType` because input schemas differ.

Current custom actor type:

- `indeed-valig` for `valig/indeed-jobs-scraper`

## Run

Search jobs and generate report:

```bash
npm run search
```

Review jobs one by one:

```bash
npm run review
```

Regenerate report from existing scored data:

```bash
npm run report
```

Re-score existing raw jobs after config/filter changes:

```bash
npm run score
```

Outputs:

- `data/raw-jobs.json`
- `data/scored-jobs.json`
- `data/reviewed-jobs.json`
- `reports/latest.md`

## How Scoring Works

Jobs get points for matching resume-aligned backend skills:

- Java
- Spring Boot
- backend
- microservices
- REST API
- Kafka
- SQL
- AWS/Azure/GCP
- Docker/Kubernetes
- GenAI/LLM/RAG when Java/backend match is strong

Jobs are rejected when they match rules such as:

- fresher/internship
- too junior or too senior
- manager-only/lead-only/architect-only
- no clear job link
- missing Java/backend signal
- older than configured posting window

## Example: 4-Year Candidate

Use:

```json
"minExperience": 4,
"maxExperience": 6,
"rejectExperiencePatterns": ["0-1", "0-2", "0-3", "7+", "8+", "9+", "10+"]
```

Good target titles:

```json
["Java Developer", "Backend Developer", "Spring Boot Developer", "Java Microservices Developer"]
```

## Example: 2-Year Candidate

Use:

```json
"minExperience": 2,
"maxExperience": 3,
"rejectExperiencePatterns": ["0-1", "4+", "5+", "6+", "7+", "8+", "10+"]
```

Good target titles:

```json
["Java Developer", "Junior Java Developer", "Associate Backend Developer", "Spring Boot Developer"]
```

Also update keywords:

```json
[
  "\"Java Developer\" \"Spring Boot\" \"2 years\"",
  "\"Junior Java Developer\" Spring Boot",
  "\"Associate Backend Developer\" Java"
]
```

## Cost Notes

Apify actor runs may cost money. Per-run cap:

```json
"apifyMaxRunCostUsd": 0.05
```

If an actor aborts before returning data, increase this slowly.

## Safety

- `.env` is ignored by Git.
- Do not commit API keys.
- Reports and raw job data are ignored by default.
- Auto-apply is intentionally not implemented.

No auto-apply is included. Review gate first.
