import re
import time
import yaml
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from agent.applicator import build_driver


def _load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_jobs(days: int = 7, max_jobs: int = 15) -> list[dict]:
    config = _load_config()
    aliases = config.get("role_aliases", [])
    max_pages = config.get("limits", {}).get("max_pages", 5)

    driver = build_driver()
    seen_urls: set[str] = set()
    all_jobs: list[dict] = []

    try:
        for role in aliases:
            if len(all_jobs) >= max_jobs:
                break
            jobs = _scrape_role_selenium(driver, role, days, max_pages, seen_urls)
            all_jobs.extend(jobs)
            print(f"  [{role}] -> {len(jobs)} new jobs found")
    finally:
        driver.quit()

    return all_jobs[:max_jobs]


def _scrape_role_selenium(driver, role: str, days: int, max_pages: int, seen_urls: set[str]) -> list[dict]:
    jobs = []
    query = role.replace(" ", "-").lower()

    for page in range(1, max_pages + 1):
        url = f"https://www.naukri.com/{query}-jobs-{page}"
        try:
            driver.get(url)
            # Wait for job cards to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".srp-jobtuple-wrapper, .cust-job-tuple, article.jobTuple"))
            )
            time.sleep(2) # Extra time for lazy content
        except Exception as exc:
            print(f"    Fetch error ({url}): {exc}")
            break

        soup = BeautifulSoup(driver.page_source, "lxml")
        cards = soup.select(".srp-jobtuple-wrapper, .cust-job-tuple, article.jobTuple, div.jobTuple")
        if not cards:
            break

        new_on_page = 0
        for card in cards:
            job_url = _extract_url(card)
            if not job_url or job_url in seen_urls:
                continue

            posted = _extract_posted(card)
            if not _within_days(posted, days):
                continue

            seen_urls.add(job_url)
            jobs.append(
                {
                    "title": _text(card, "a.title, .title"),
                    "company": _text(card, ".comp-name, .companyInfo strong"),
                    "url": job_url,
                    "posted": posted,
                    "snippet": _text(card, ".job-desc, .jobDescription"),
                }
            )
            new_on_page += 1

        if new_on_page == 0:
            break

    return jobs


def fetch_jd(url: str) -> str:
    # We'll use a temporary driver for JD fetch to avoid complicating fetch_jobs
    # or we could pass the driver around. For simplicity, we'll open a new one
    # if this is called outside the main loop, but run.py calls it inside.
    # Actually, fetch_jobs returns jobs, then run.py calls fetch_jd for each.
    # Let's use a single driver in run.py instead? No, let's keep it simple here.
    
    driver = build_driver()
    try:
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "lxml")
        for selector in [".job-desc", ".jobDescription", ".jd-desc", "#job_description"]:
            element = soup.select_one(selector)
            if element:
                return element.get_text(" ", strip=True)
        return soup.get_text(" ", strip=True)[:3000]
    except Exception as exc:
        print(f"    JD fetch error: {exc}")
        return ""
    finally:
        driver.quit()



def extract_keywords(jd_text: str) -> list[str]:
    """
    Returns JD keywords that overlap with the configured skill vocabulary.
    This does not invent new skills.
    """
    config = _load_config()
    aliases = config.get("keyword_aliases", {})
    categories = config.get("skill_categories", {})

    vocab: set[str] = set()
    for items in categories.values():
        for item in items:
            vocab.add(item.lower())
    for keyword in aliases:
        vocab.add(keyword.lower())

    jd_lower = jd_text.lower()
    matched: list[str] = []
    matched_set: set[str] = set()

    for term in sorted(vocab, key=len, reverse=True):
        if term in jd_lower and term not in matched_set:
            matched.append(term)
            matched_set.add(term)

    return matched


def _text(card, selector: str) -> str:
    element = card.select_one(selector)
    return element.get_text(strip=True) if element else ""


def _extract_url(card) -> str:
    for selector in ["a.title", "a[href*='naukri.com']", "a"]:
        element = card.select_one(selector)
        if element and element.get("href"):
            href = element["href"]
            if "naukri.com" in href or href.startswith("/"):
                return "https://www.naukri.com" + href if href.startswith("/") else href
    return ""


def _extract_posted(card) -> str:
    for selector in [".jobTupleFooter .ellipsis", ".job-post-day", ".posted-day"]:
        element = card.select_one(selector)
        if element:
            return element.get_text(strip=True).lower()
    return ""


def _within_days(posted_text: str, days: int) -> bool:
    if not posted_text:
        return True
    if "today" in posted_text or "hour" in posted_text or "just now" in posted_text:
        return True
    match = re.search(r"(\d+)\s*day", posted_text)
    if match:
        return int(match.group(1)) <= days
    match = re.search(r"(\d+)\s*week", posted_text)
    if match:
        return int(match.group(1)) * 7 <= days
    return True

