import * as cheerio from "cheerio";

const USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36";
const REQUEST_TIMEOUT_MS = 8000;

export async function runWebSearch({ platform, keyword }) {
  const query = `site:${platform.domain} ${keyword}`;
  const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;

  try {
    const res = await timedFetch(url);
    if (!res.ok) return { jobs: [], note: `Search blocked/status ${res.status}` };
    const html = await res.text();
    const $ = cheerio.load(html);
    const jobs = [];

    $(".result").slice(0, 8).each((_, el) => {
      const a = $(el).find(".result__a").first();
      const snippet = $(el).find(".result__snippet").text().replace(/\s+/g, " ").trim();
      const rawHref = a.attr("href") || "";
      const link = decodeDuckDuckGoLink(rawHref);
      if (!link || !link.includes(platform.domain)) return;

      jobs.push({
        title: a.text().replace(/\s+/g, " ").trim(),
        company: "",
        platform: platform.name,
        sourceDomain: platform.domain,
        location: "",
        mode: inferMode(`${a.text()} ${snippet}`),
        postedDate: inferPostedDate(`${a.text()} ${snippet}`),
        experience: inferExperience(`${a.text()} ${snippet}`),
        salary: "",
        link,
        description: snippet,
        keyword,
        source: "web-search"
      });
    });

    return { jobs, note: jobs.length ? `Web search returned ${jobs.length} candidates` : "No public indexed results" };
  } catch (error) {
    return { jobs: [], note: `Web search failed: ${error.message}` };
  }
}

async function timedFetch(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { headers: { "user-agent": USER_AGENT }, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

function decodeDuckDuckGoLink(rawHref) {
  if (!rawHref) return "";
  try {
    const url = new URL(rawHref, "https://duckduckgo.com");
    const uddg = url.searchParams.get("uddg");
    return uddg ? decodeURIComponent(uddg) : url.href;
  } catch {
    return rawHref;
  }
}

function inferMode(text) {
  const lower = text.toLowerCase();
  if (lower.includes("remote")) return "Remote";
  if (lower.includes("hybrid")) return "Hybrid";
  if (lower.includes("onsite") || lower.includes("on-site")) return "Onsite";
  return "";
}

function inferExperience(text) {
  const match = text.match(/(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years|yrs|yr)/i) || text.match(/(\d+)\+?\s*(?:years|yrs|yr)/i);
  return match ? match[0] : "";
}

function inferPostedDate(text) {
  const match = text.match(/(?:today|yesterday|\d+\s+(?:hour|hours|day|days)\s+ago|posted\s+\w+\s+\d{1,2})/i);
  return match ? match[0] : "";
}
