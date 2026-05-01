import * as cheerio from "cheerio";

const DIRECT_PLATFORMS = new Set(["remotive.com", "workingnomads.com", "weworkremotely.com"]);
const USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36";

export function hasDirectSearch(platform) {
  return DIRECT_PLATFORMS.has(platform.domain);
}

export async function runDirectSearch({ platform, keyword }) {
  if (platform.domain === "remotive.com") return searchRemotive(platform, keyword);
  if (platform.domain === "workingnomads.com") return searchWorkingNomads(platform, keyword);
  if (platform.domain === "weworkremotely.com") return searchWeWorkRemotely(platform, keyword);
  return { jobs: [], note: "No direct adapter" };
}

async function searchWeWorkRemotely(platform, keyword) {
  const url = "https://weworkremotely.com/categories/remote-programming-jobs.rss";
  const res = await fetch(url, { headers: { "user-agent": USER_AGENT } });
  if (!res.ok) return { jobs: [], note: `RSS status ${res.status}` };
  const xml = await res.text();
  const $ = cheerio.load(xml, { xmlMode: true });
  const terms = toPlainQuery(keyword).split(/\s+/).filter(Boolean);
  const jobs = [];

  $("item").each((_, item) => {
    const titleText = $(item).find("title").first().text().trim();
    const description = htmlText($(item).find("description").first().text());
    const haystack = `${titleText} ${description}`.toLowerCase();
    if (!terms.some((term) => haystack.includes(term))) return;

    const [company, ...titleParts] = titleText.split(":");
    jobs.push({
      title: (titleParts.join(":").trim() || titleText),
      company: titleParts.length ? company.trim() : "",
      platform: platform.name,
      sourceDomain: platform.domain,
      location: $(item).find("region").first().text().trim(),
      mode: "Remote",
      postedDate: $(item).find("pubDate").first().text().trim(),
      experience: inferExperience(description),
      salary: "",
      link: $(item).find("link").first().text().trim(),
      description,
      keyword,
      source: "rss"
    });
  });

  return { jobs, note: `RSS returned ${jobs.length} matching jobs` };
}

async function searchRemotive(platform, keyword) {
  const url = `https://remotive.com/api/remote-jobs?category=software-dev&search=${encodeURIComponent(toPlainQuery(keyword))}`;
  const res = await fetch(url, { headers: { "user-agent": USER_AGENT } });
  if (!res.ok) return { jobs: [], note: `Direct API status ${res.status}` };
  const body = await res.json();
  const jobs = (body.jobs || []).map((item) => ({
    title: item.title || "",
    company: item.company_name || "",
    platform: platform.name,
    sourceDomain: platform.domain,
    location: item.candidate_required_location || "",
    mode: "Remote",
    postedDate: item.publication_date || "",
    experience: "",
    salary: item.salary || "",
    link: item.url || "",
    description: htmlText(item.description || ""),
    keyword,
    source: "direct-api"
  }));
  return { jobs, note: `Direct API returned ${jobs.length} jobs` };
}

async function searchWorkingNomads(platform, keyword) {
  const url = `https://www.workingnomads.com/api/exposed_jobs/?category=development&search=${encodeURIComponent(toPlainQuery(keyword))}`;
  const res = await fetch(url, { headers: { "user-agent": USER_AGENT } });
  if (!res.ok) return { jobs: [], note: `Direct API status ${res.status}` };
  const body = await res.json();
  const jobs = (Array.isArray(body) ? body : []).map((item) => ({
    title: item.title || "",
    company: item.company || item.company_name || "",
    platform: platform.name,
    sourceDomain: platform.domain,
    location: item.location || item.regions?.join(", ") || "",
    mode: "Remote",
    postedDate: item.pub_date || item.publication_date || item.created_at || "",
    experience: "",
    salary: item.salary || "",
    link: item.url || "",
    description: htmlText(item.description || ""),
    keyword,
    source: "direct-api"
  }));
  return { jobs, note: `Direct API returned ${jobs.length} jobs` };
}

function toPlainQuery(keyword) {
  const lower = keyword.toLowerCase();
  if (lower.includes("spring boot")) return "spring boot";
  if (lower.includes("microservices")) return "java microservices";
  if (lower.includes("kafka")) return "java kafka";
  if (lower.includes("genai") || lower.includes("llm") || lower.includes("rag")) return "java ai";
  return "java";
}

function htmlText(html) {
  return cheerio.load(html).text().replace(/\s+/g, " ").trim();
}

function inferExperience(text) {
  const match = text.match(/(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years|yrs|yr)/i) || text.match(/(\d+)\+?\s*(?:years|yrs|yr)/i);
  return match ? match[0] : "";
}
