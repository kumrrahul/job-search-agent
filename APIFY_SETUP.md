# Apify Setup

This project can run public/direct job searches without Apify, but Apify improves coverage for boards such as Indeed, Glassdoor, Naukri, Wellfound, and freelance/job platforms.

## 1. Get Apify API key

1. Open https://console.apify.com
2. Log in.
3. Go to Settings.
4. Open Integrations or API tokens.
5. Copy your API token.

Do not commit or share this token.

## 2. Add key locally

Create a `.env` file in project root:

```env
APIFY_TOKEN=apify_api_your_token_here
```

This file is ignored by Git through `.gitignore`.

## 3. Configure actors

Open:

```txt
config/jobs.config.json
```

Each platform can use an Apify actor:

```json
{
  "name": "Indeed",
  "domain": "indeed.com",
  "actorId": "valig/indeed-jobs-scraper",
  "actorInputType": "indeed-valig",
  "enabled": true
}
```

For platforms without an actor, keep:

```json
"actorId": null
```

The project will use direct APIs/RSS or web-search fallback.

## 4. Test token

Run:

```bash
npm run search
```

If token works, platform coverage will show actor notes like:

```txt
Actor valig/indeed-jobs-scraper returned N items
```

## 5. Cost control

Config has a per-run cap:

```json
"apifyMaxRunCostUsd": 0.05
```

Increase only if needed. Some actors need more startup budget before returning data.

## 6. Adding new actor types

Actors use different input schemas. If a new actor does not return correct results:

1. Open actor page on Apify.
2. Check its Input tab.
3. Add `actorId` in config.
4. Add a matching input builder in `src/search/apify.js` if generic fields do not work.

Current custom adapter:

- `indeed-valig` for `valig/indeed-jobs-scraper`

