const IMPORTANT = new Map([
  ["java", 14],
  ["spring boot", 14],
  ["backend", 8],
  ["microservices", 9],
  ["rest api", 7],
  ["kafka", 7],
  ["sql", 6],
  ["aws", 5],
  ["azure", 5],
  ["gcp", 5],
  ["docker", 4],
  ["kubernetes", 4],
  ["junit", 3],
  ["mockito", 3],
  ["openapi", 3],
  ["genai", 4],
  ["llm", 4],
  ["rag", 4],
  ["agentic ai", 4]
]);

export function scoreJobs(jobs, resume, config) {
  return jobs.map((job) => scoreJob(job, resume, config)).sort((a, b) => b.matchScore - a.matchScore);
}

function scoreJob(job, resume, config) {
  const text = `${job.title} ${job.company} ${job.location} ${job.mode} ${job.experience} ${job.description}`.toLowerCase();
  const matchedSkills = [];
  const missingSkills = [];
  let score = 20;

  for (const [skill, points] of IMPORTANT) {
    if (hasSkill(text, skill)) {
      matchedSkills.push(skill);
      score += points;
    } else if (resume.strongestSkills.includes(skill) || config.preferredSkills.includes(skill)) {
      missingSkills.push(skill);
    }
  }

  const rejectReasons = reject(job, text, config);
  const risks = [];

  if (!job.postedDate) risks.push("Posted date unclear");
  if (!job.experience) risks.push("Experience requirement unclear");
  if (/\b(genai|llm|rag|agentic|ai)\b/i.test(text) && !(hasSkill(text, "java") || hasSkill(text, "spring boot") || hasSkill(text, "backend"))) {
    rejectReasons.push("AI role lacks strong Java/backend match");
  }

  if (rejectReasons.length) score = Math.min(score, 49);
  if (risks.length) score -= 8;

  score = Math.max(0, Math.min(100, score));

  return {
    ...job,
    matchedSkills,
    missingSkills: missingSkills.slice(0, 10),
    matchScore: score,
    reason: buildReason(matchedSkills, job),
    risks,
    rejectReasons,
    status: rejectReasons.length ? "rejected" : risks.length ? "needs_review" : "accepted"
  };
}

function reject(job, text, config) {
  const reasons = [];
  const title = String(job.title || "").toLowerCase();

  if (!job.link) reasons.push("Missing job link");
  for (const term of config.filters.rejectTitleTerms) {
    if (title.includes(term)) reasons.push(`Rejected title term: ${term}`);
  }
  for (const term of config.filters.rejectNonTargetTitleTerms || []) {
    if (title.includes(term)) reasons.push(`Rejected non-target title term: ${term}`);
  }
  for (const pattern of config.filters.rejectExperiencePatterns) {
    if (text.includes(pattern)) reasons.push(`Rejected experience pattern: ${pattern}`);
  }

  const expRange = extractExperienceRange(`${job.experience} ${job.description} ${job.title}`);
  if (expRange) {
    if (expRange.min < config.filters.minExperience) reasons.push(`Experience too low: ${expRange.raw}`);
    if (expRange.max > config.filters.maxExperience && expRange.min > config.filters.maxExperience) {
      reasons.push(`Experience too high: ${expRange.raw}`);
    }
  }

  if (!hasSkill(text, "java")) reasons.push("Missing required signal: java");
  if (!["spring boot", "spring", "backend", "microservices", "rest api", "restful"].some((signal) => hasSkill(text, signal))) {
    reasons.push("Missing backend-family signal: spring/backend/microservices/rest api");
  }

  const parsedDate = parsePostedDate(job.postedDate);
  if (parsedDate) {
    const ageDays = (Date.now() - parsedDate.getTime()) / 86400000;
    if (ageDays > config.filters.postedWithinDays) reasons.push(`Posted older than ${config.filters.postedWithinDays} days`);
  }

  return [...new Set(reasons)];
}

function hasSkill(text, skill) {
  const escaped = skill.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+");
  return new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`, "i").test(text);
}

function parsePostedDate(value = "") {
  if (!value) return null;
  const text = String(value).trim().toLowerCase();
  if (text === "today") return new Date();
  if (text === "yesterday") return new Date(Date.now() - 86400000);
  const ago = text.match(/(\d+)\s+(hour|hours|day|days)\s+ago/);
  if (ago) {
    const amount = Number(ago[1]);
    const unit = ago[2].startsWith("hour") ? 3600000 : 86400000;
    return new Date(Date.now() - amount * unit);
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function extractExperienceRange(text) {
  const range = text.match(/(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years|yrs|yr)/i);
  if (range) return { min: Number(range[1]), max: Number(range[2]), raw: range[0] };

  const plus = text.match(/(\d+)\+?\s*(?:years|yrs|yr)/i);
  if (plus) {
    const min = Number(plus[1]);
    return { min, max: plus[0].includes("+") ? 99 : min, raw: plus[0] };
  }
  return null;
}

function buildReason(matchedSkills, job) {
  const top = matchedSkills.slice(0, 7).join(", ");
  return top ? `Matches ${top}` : `Weak keyword match for ${job.keyword}`;
}
