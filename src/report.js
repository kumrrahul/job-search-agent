export function buildReport({ resume, coverage, scoredJobs, dateChecked }) {
  const accepted = scoredJobs.filter((job) => job.status === "accepted").slice(0, 20);
  const review = scoredJobs.filter((job) => job.status === "needs_review").slice(0, 20);
  const rejected = scoredJobs.filter((job) => job.status === "rejected").slice(0, 30);
  const top = accepted.length ? accepted : review.slice(0, 20);
  const bestFive = top.slice(0, 5);
  const gaps = aggregateGaps(top);

  return [
    `# Java Backend Job Search Report`,
    ``,
    `Date checked: ${dateChecked}`,
    ``,
    `## 1. Resume Keyword Summary`,
    ``,
    `Best-fit titles: ${resume.bestFitTitles.join(", ")}.`,
    ``,
    `Strongest skills: ${resume.strongestSkills.join(", ")}.`,
    ``,
    `## 2. Platform Search Coverage`,
    ``,
    `| Platform | Searched? | Results Found | Notes |`,
    `|---|---:|---:|---|`,
    ...coverage.map((row) => `| ${esc(row.platform)} | ${row.searched ? "Yes" : "No"} | ${row.resultsFound} | ${esc(trim(row.notes, 180))} |`),
    ``,
    `## 3. Top Matching Jobs`,
    ``,
    top.length < 20 ? `Strict filters found ${top.length} usable/review-needed jobs, fewer than 20.` : `Top 20 strict matches below.`,
    ``,
    `| Rank | Job Title | Company | Platform | Location | Mode | Posted Date | Experience | Match Score | Link |`,
    `|---:|---|---|---|---|---|---|---|---:|---|`,
    ...top.map((job, index) => jobRow(job, index)),
    ``,
    `## 4. Best 5 Jobs`,
    ``,
    ...bestFive.map((job, index) => `${index + 1}. **${esc(job.title || "Untitled")}**${job.company ? ` - ${esc(job.company)}` : ""}: ${esc(job.reason)}. Risk: ${esc(job.risks.join("; ") || "None captured")}.`),
    ``,
    `## 5. Rejected / Skipped Sources`,
    ``,
    ...rejected.slice(0, 15).map((job) => `- ${esc(job.platform)}: ${esc(job.title || job.link)} - ${esc(job.rejectReasons.join("; "))}`),
    rejected.length ? `` : `No rejected jobs captured.`,
    ``,
    `## 6. Skills Gap`,
    ``,
    ...(gaps.length ? gaps.map(([skill, count]) => `- ${skill}: missing in ${count} top listings`) : [`- No repeated gaps among top matches.`]),
    ``,
    `## 7. Recruiter Messages`,
    ``,
    `Recruiter DM:`,
    ``,
    `Hi, I’m Rahul Kumar, Java Backend Developer with 4+ years at Oracle/Genpact. Strong in Java 17, Spring Boot, REST APIs, microservices, Kafka, SQL, Docker/Kubernetes, and AI-assisted development with Claude/Codex. Interested in this backend role and can share resume.`,
    ``,
    `Email:`,
    ``,
    `Subject: Java Backend Developer - Spring Boot/Microservices`,
    ``,
    `Hi, I’m Rahul Kumar, Java Backend Developer with 4+ years building enterprise microservices at Oracle and Genpact. My core stack: Java, Spring Boot, REST APIs, Kafka, SQL/Oracle, Docker, Kubernetes, JUnit/Mockito, and cloud-native backend systems. I’m interested in the role and believe my Oracle microservice experience aligns well. Resume attached.`,
    ``,
    `Freelance proposal:`,
    ``,
    `Hi, I can build this Java/Spring Boot microservice backend with clean REST APIs, Kafka-style event flow, SQL schema design, Swagger/OpenAPI docs, Docker setup, and JUnit/Mockito tests. I have 4+ years backend experience at Oracle/Genpact with production microservices, Kafka, SQL, Docker, Kubernetes, and API design.`,
    ``
  ].join("\n");
}

function jobRow(job, index) {
  return [
    index + 1,
    esc(job.title || "Untitled"),
    esc(job.company || "Unknown"),
    esc(job.platform),
    esc(job.location || "Unknown"),
    esc(job.mode || "Unknown"),
    esc(job.postedDate || "Unclear"),
    esc(job.experience || "Unclear"),
    job.matchScore,
    job.link ? `[Link](${job.link})` : ""
  ].join(" | ").replace(/^/, "| ").replace(/$/, " |");
}

function aggregateGaps(jobs) {
  const counts = new Map();
  for (const job of jobs) {
    for (const skill of job.missingSkills || []) counts.set(skill, (counts.get(skill) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
}

function esc(value = "") {
  return String(value).replaceAll("|", "\\|").replace(/\s+/g, " ").trim();
}

function trim(value, max) {
  const text = String(value || "");
  return text.length > max ? `${text.slice(0, max - 3)}...` : text;
}

