import time

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from agent import secrets


def _build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)


def fetch_profile() -> dict:
    """
    Logs into Naukri and reads the current role and experience.
    Falls back to config.yaml role_aliases[0] if profile parsing fails.
    """
    driver = _build_driver()
    try:
        driver.get("https://www.naukri.com/mnjuser/profile")
        wait = WebDriverWait(driver, 15)

        wait.until(EC.presence_of_element_located((By.ID, "usernameField")))
        driver.find_element(By.ID, "usernameField").send_keys(secrets.get("NAUKRI_EMAIL"))
        driver.find_element(By.ID, "passwordField").send_keys(secrets.get("NAUKRI_PASSWORD"))
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        time.sleep(4)

        role = _safe_text(driver, [".designation", ".curr-desig", "[class*='designation']"])
        exp = _safe_text(driver, [".expLevel", ".exp-years", "[class*='experience']"])

        if not role:
            with open("config.yaml", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            role = cfg.get("role_aliases", ["Software Engineer"])[0]

        return {"role": role.strip(), "experience": exp.strip() or "3+ years"}
    finally:
        driver.quit()


def _safe_text(driver, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            if element and element.text.strip():
                return element.text.strip()
        except Exception:
            pass
    return ""

