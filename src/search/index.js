import { runActorSearch } from "./apify.js";
import { hasDirectSearch, runDirectSearch } from "./direct.js";
import { runWebSearch } from "./web.js";

export async function searchAll(config) {
  const tasks = [];

  for (const platform of config.platforms.filter((p) => p.enabled)) {
    for (const keyword of config.keywords) tasks.push({ platform, keyword });
  }

  const results = await mapLimit(tasks, config.searchConcurrency || 10, async ({ platform, keyword }) => {
      const result = platform.actorId
        ? await runActorSearch({ platform, keyword, config })
        : hasDirectSearch(platform)
          ? await runDirectSearch({ platform, keyword, config })
        : await runWebSearch({ platform, keyword, config });

      return { platform: platform.name, keyword, ...result };
  });

  const rawJobs = [];
  const byPlatform = new Map();
  for (const platform of config.platforms.filter((p) => p.enabled)) {
    byPlatform.set(platform.name, { platform: platform.name, searched: true, resultsFound: 0, notes: [] });
  }

  for (const result of results) {
    rawJobs.push(...result.jobs);
    const row = byPlatform.get(result.platform);
    row.resultsFound += result.jobs.length;
    if (result.note) row.notes.push(`${result.keyword}: ${result.note}`);
  }

  const coverage = [];
  for (const row of byPlatform.values()) {
    let platformCount = 0;
    platformCount = row.resultsFound;
    coverage.push({
      platform: row.platform,
      searched: row.searched,
      resultsFound: platformCount,
      notes: row.notes.join(" | ") || "No result"
    });
  }

  return { rawJobs, coverage };
}

async function mapLimit(items, limit, mapper) {
  const results = new Array(items.length);
  let next = 0;

  async function worker() {
    while (next < items.length) {
      const index = next++;
      results[index] = await mapper(items[index], index);
    }
  }

  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}
