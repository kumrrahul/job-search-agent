export function dedupeJobs(jobs) {
  const seen = new Set();
  const deduped = [];

  for (const job of jobs) {
    const key = [
      clean(job.company) || host(job.link),
      clean(job.title),
      clean(job.location)
    ].join("|");

    if (!job.link || seen.has(key)) continue;
    seen.add(key);
    deduped.push(job);
  }

  return deduped;
}

function clean(value = "") {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function host(link = "") {
  try {
    return new URL(link).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

