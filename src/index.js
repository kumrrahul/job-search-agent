import "dotenv/config";
import { existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { readJson, writeJson, writeText } from "./fs.js";
import { parseResume } from "./resume.js";
import { searchAll } from "./search/index.js";
import { dedupeJobs } from "./normalize.js";
import { scoreJobs } from "./score.js";
import { buildReport } from "./report.js";
import { reviewJobs } from "./review.js";

const command = process.argv[2] || "search";
const root = process.cwd();
const configPath = `${root}/config/jobs.config.json`;
const dataDir = `${root}/data`;
const reportsDir = `${root}/reports`;

async function main() {
  await mkdir(dataDir, { recursive: true });
  await mkdir(reportsDir, { recursive: true });

  const config = await readJson(configPath);

  if (command === "search") {
    const resume = await parseResume(config.resumePath);
    const { rawJobs, coverage } = await searchAll(config);
    const deduped = dedupeJobs(rawJobs);
    const scoredJobs = scoreJobs(deduped, resume, config);
    const dateChecked = new Intl.DateTimeFormat("en-IN", {
      dateStyle: "full",
      timeStyle: "short",
      timeZone: config.dateCheckedTimezone
    }).format(new Date());

    await writeJson(`${dataDir}/resume-summary.json`, resumeSummary(resume));
    await writeJson(`${dataDir}/raw-jobs.json`, { dateChecked, rawJobs, deduped });
    await writeJson(`${dataDir}/coverage.json`, coverage);
    await writeJson(`${dataDir}/scored-jobs.json`, scoredJobs);
    await writeText(`${reportsDir}/latest.md`, buildReport({ resume, coverage, scoredJobs, dateChecked }));
    console.log(`Search complete. Raw: ${rawJobs.length}, deduped: ${deduped.length}, scored: ${scoredJobs.length}`);
    console.log(`${reportsDir}/latest.md`);
    return;
  }

  if (command === "score") {
    const resume = await parseResume(config.resumePath);
    const rawPath = `${dataDir}/raw-jobs.json`;
    if (!existsSync(rawPath)) throw new Error("Run npm run search first.");
    const raw = await readJson(rawPath);
    const coverage = existsSync(`${dataDir}/coverage.json`) ? await readJson(`${dataDir}/coverage.json`) : [];
    const deduped = raw.deduped || dedupeJobs(raw.rawJobs || []);
    const scoredJobs = scoreJobs(deduped, resume, config);
    const dateChecked = raw.dateChecked || new Intl.DateTimeFormat("en-IN", {
      dateStyle: "full",
      timeStyle: "short",
      timeZone: config.dateCheckedTimezone
    }).format(new Date());
    await writeJson(`${dataDir}/scored-jobs.json`, scoredJobs);
    await writeText(`${reportsDir}/latest.md`, buildReport({ resume, coverage, scoredJobs, dateChecked }));
    console.log(`Score complete. Scored: ${scoredJobs.length}`);
    return;
  }

  if (command === "review") {
    const scoredPath = `${dataDir}/scored-jobs.json`;
    if (!existsSync(scoredPath)) throw new Error("Run npm run search first.");
    const scoredJobs = await readJson(scoredPath);
    const reviewed = await reviewJobs(scoredJobs);
    await writeJson(`${dataDir}/reviewed-jobs.json`, reviewed);
    console.log(`Reviewed ${reviewed.length} jobs.`);
    return;
  }

  if (command === "report") {
    const config = await readJson(configPath);
    const resume = await parseResume(config.resumePath);
    const coverage = await readJson(`${dataDir}/coverage.json`);
    const scoredJobs = await readJson(`${dataDir}/scored-jobs.json`);
    const dateChecked = new Intl.DateTimeFormat("en-IN", {
      dateStyle: "full",
      timeStyle: "short",
      timeZone: config.dateCheckedTimezone
    }).format(new Date());
    await writeText(`${reportsDir}/latest.md`, buildReport({ resume, coverage, scoredJobs, dateChecked }));
    console.log(`${reportsDir}/latest.md`);
    return;
  }

  throw new Error(`Unknown command: ${command}`);
}

function resumeSummary(resume) {
  return {
    path: resume.path,
    years: resume.years,
    strongestSkills: resume.strongestSkills,
    bestFitTitles: resume.bestFitTitles
  };
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
