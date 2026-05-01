import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

export async function reviewJobs(scoredJobs) {
  const rl = readline.createInterface({ input, output });
  const reviewed = [];

  for (const job of scoredJobs.filter((item) => item.status !== "rejected").slice(0, 50)) {
    console.log("\n---");
    console.log(`${job.title} | ${job.company || "Unknown"} | ${job.platform} | ${job.matchScore}`);
    console.log(job.link);
    console.log(`Reason: ${job.reason}`);
    if (job.risks.length) console.log(`Risks: ${job.risks.join("; ")}`);
    const answer = (await rl.question("Approve? [y]es / [s]kip / [q]uit: ")).trim().toLowerCase();
    if (answer === "q") break;
    reviewed.push({ ...job, reviewDecision: answer === "y" ? "approved" : "skipped" });
  }

  rl.close();
  return reviewed;
}

