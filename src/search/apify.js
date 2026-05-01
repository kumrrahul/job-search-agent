import { ApifyClient } from "apify-client";

export async function runActorSearch({ platform, keyword, config }) {
  const token = process.env.APIFY_TOKEN;
  if (!token || !platform.actorId) {
    return { jobs: [], note: !token ? "APIFY_TOKEN missing" : "No actorId configured" };
  }

  const client = new ApifyClient({ token });
  const input = buildInput(platform, keyword, config);

  const run = await client.actor(platform.actorId).call(input, { maxTotalChargeUsd: config.apifyMaxRunCostUsd || 0.25 });
  const { items } = await client.dataset(run.defaultDatasetId).listItems({ limit: 100 });

  return {
    jobs: items.map((item) => normalizeActorItem(item, platform, keyword)),
    note: `Actor ${platform.actorId} returned ${items.length} items`
  };
}

function normalizeActorItem(item, platform, keyword) {
  return {
    title: item.title || item.jobTitle || item.positionName || item.name || "",
    company: normalizeCompany(item.company || item.companyName || item.hiringOrganization || ""),
    platform: platform.name,
    sourceDomain: platform.domain,
    location: normalizeLocation(item.location || item.jobLocation || item.address || ""),
    mode: item.remote ? "Remote" : item.workplaceType || item.mode || "",
    postedDate: item.postedDate || item.datePosted || item.datePublished || item.publishedAt || item.createdAt || "",
    experience: item.experience || item.experienceRequired || item.seniority || "",
    salary: item.salary || item.compensation || "",
    link: item.url || item.link || item.jobUrl || item.applyUrl || "",
    description: item.description || item.jobDescription || item.snippet || "",
    keyword,
    source: "apify"
  };
}

function buildInput(platform, keyword, config) {
  if (platform.actorInputType === "indeed-valig") {
    return {
      title: toIndeedTitle(keyword),
      location: "remote",
      country: "in",
      limit: 10,
      datePosted: String(config.filters.postedWithinDays)
    };
  }

  return {
    query: keyword,
    search: keyword,
    keyword,
    keywords: keyword,
    maxItems: 25,
    limit: 25,
    datePosted: String(config.filters.postedWithinDays),
    postedWithinDays: config.filters.postedWithinDays,
    minSalary: config.filters.minSalary,
    maxSalary: config.filters.maxSalary
  };
}

function toIndeedTitle(keyword) {
  const lower = keyword.toLowerCase();
  if (lower.includes("spring boot")) return "Java Spring Boot Developer";
  if (lower.includes("microservices")) return "Java Microservices Developer";
  if (lower.includes("kafka")) return "Java Backend Engineer Kafka";
  if (lower.includes("genai") || lower.includes("llm") || lower.includes("rag")) return "Java GenAI Backend Developer";
  return "Java Backend Developer";
}

function normalizeCompany(company) {
  if (!company || typeof company === "string") return company || "";
  return company.name || company.displayName || "";
}

function normalizeLocation(location) {
  if (!location || typeof location === "string") return location || "";
  return [location.city, location.admin1Code, location.countryName].filter(Boolean).join(", ");
}
