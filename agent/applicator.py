import time
from pathlib import Path

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from agent import secrets


def _load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_driver() -> webdriver.Chrome:
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


def login(driver: webdriver.Chrome) -> None:
    driver.get("https://www.naukri.com/mnjuser/profile")
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.ID, "usernameField")))
    driver.find_element(By.ID, "usernameField").send_keys(secrets.get("NAUKRI_EMAIL"))
    driver.find_element(By.ID, "passwordField").send_keys(secrets.get("NAUKRI_PASSWORD"))
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    time.sleep(4)
    print("  Logged into Naukri")


def upload_profile_resume(driver: webdriver.Chrome, pdf_path: Path) -> bool:
    """Uploads the tailored PDF to the Naukri profile."""
    try:
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(3)
        # Look for the Update Resume file input
        # Usually it's an invisible input triggered by a button
        upload = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file'][id='attachCV']"))
        )
        upload.send_keys(str(pdf_path.resolve()))
        time.sleep(5) # Wait for upload to complete
        print(f"  Uploaded resume to profile: {pdf_path.name}")
        return True
    except Exception as exc:
        print(f"  Resume profile upload failed: {exc}")
        return False


def apply_to_job(job: dict, pdf_path: Path, driver: webdriver.Chrome) -> dict:
    """
    Attempts to apply to a single job.
    Returns status: applied, already_applied, or failed.
    """
    result = {
        "title": job["title"],
        "company": job["company"],
        "url": job["url"],
        "pdf": str(pdf_path),
        "status": "failed",
        "error": "",
        "application_notes": [],
    }
    if job.get("resume_warning"):
        result["resume_warning"] = job["resume_warning"]
    if job.get("resume_pages"):
        result["resume_pages"] = job["resume_pages"]

    try:
        driver.get(job["url"])
        wait = WebDriverWait(driver, 12)
        time.sleep(2)

        if _has_applied_state(driver):
            result["status"] = "already_applied"
            return result

        apply_btn = None
        for selector in [
            "button.apply-button",
            "button[data-ga-label='Apply']",
            "button[data-ga-label='Share My Interest']",
            "a.apply-button",
            "button[class*='apply']",
            "//button[contains(text(),'Share My Interest')]",
            "//button[contains(text(),'Apply')]",
        ]:
            try:
                locator = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                apply_btn = wait.until(EC.element_to_be_clickable((locator, selector)))
                break
            except Exception:
                continue

        if not apply_btn:
            result["error"] = "Apply button not found"
            return result

        apply_btn.click()
        time.sleep(2)

        if _has_applied_state(driver):
            result["status"] = "applied"
            result["application_notes"].append("Application completed; page changed to Applied.")
            return result

        try:
            upload = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            upload.send_keys(str(pdf_path.resolve()))
            time.sleep(1)
        except Exception:
            pass

        prompt_status = _complete_application_prompts(driver, result)
        if prompt_status:
            result["status"] = prompt_status
            return result

        if _has_applied_state(driver) or _verify_applied_after_reload(driver, job["url"], result):
            result["status"] = "applied"
            return result

        result["error"] = "Submit button not found after clicking Apply or answering prompts"
    except Exception as exc:
        result["error"] = str(exc)

    if result["status"] == "failed" and _verify_applied_after_reload(driver, job["url"], result):
        result["status"] = "applied"
        result["error"] = ""

    return result


def _complete_application_prompts(driver: webdriver.Chrome, result: dict) -> str | None:
    """
    Handles common Naukri post-Apply prompts. Returns final status when known.
    """
    config = _load_config()
    answers = config.get("application_answers", {})
    known_skills = _known_skills(config)

    for _ in range(10):
        time.sleep(1)
        if _has_applied_state(driver):
            return "already_applied"
        page_text = driver.page_source.lower()
        if any(text in page_text for text in ["application submitted", "successfully applied", "applied successfully"]):
            return "applied"

        answered = _answer_visible_fields(driver, answers, known_skills, result)
        clicked = _click_next_submit(driver)
        if clicked:
            time.sleep(2)
            continue
        if answered:
            continue
        break

    page_text = driver.page_source.lower()
    if any(text in page_text for text in ["application submitted", "successfully applied", "applied successfully"]):
        return "applied"
    if _has_applied_state(driver):
        return "already_applied"
    return None


def _has_applied_state(driver: webdriver.Chrome) -> bool:
    page_text = driver.page_source.lower()
    if any(text in page_text for text in ["already applied", "applied successfully", "application submitted"]):
        return True

    for xpath in [
        "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applied')]",
        "//span[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applied')]",
        "//div[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applied')]",
    ]:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if any(element.is_displayed() for element in elements):
                return True
        except Exception:
            continue
    return False


def _verify_applied_after_reload(driver: webdriver.Chrome, url: str, result: dict) -> bool:
    try:
        driver.get(url)
        time.sleep(3)
        if _has_applied_state(driver):
            result["application_notes"].append("Verified applied state after reloading job page.")
            return True
    except Exception as exc:
        result["application_notes"].append(f"Applied-state verification failed: {exc}")
    return False


def _answer_visible_fields(driver: webdriver.Chrome, answers: dict, known_skills: set[str], result: dict) -> bool:
    changed = False

    for field in driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), textarea"):
        try:
            input_type = (field.get_attribute("type") or "").lower()
            if input_type in {"file", "submit", "button", "checkbox", "radio"}:
                continue
            if not field.is_displayed() or field.get_attribute("value"):
                continue

            question = _question_text(driver, field)
            answer = _answer_for_question(question, answers, known_skills)
            if answer is None:
                result["application_notes"].append(f"Unanswered prompt: {question[:120]}")
                continue

            field.clear()
            field.send_keys(answer)
            result["application_notes"].append(f"Answered prompt: {question[:80]} -> {answer}")
            changed = True
        except Exception as exc:
            result["application_notes"].append(f"Prompt input error: {exc}")

    changed = _answer_radio_checkbox_groups(driver, answers, known_skills, result) or changed
    changed = _answer_selects(driver, answers, known_skills, result) or changed
    return changed


def _question_text(driver: webdriver.Chrome, element) -> str:
    label_text = ""
    element_id = element.get_attribute("id")
    if element_id:
        labels = driver.find_elements(By.CSS_SELECTOR, f"label[for='{element_id}']")
        label_text = " ".join(label.text for label in labels if label.text)

    if label_text:
        return label_text.strip()

    return driver.execute_script(
        """
        const el = arguments[0];
        const node = el.closest('li, div, section, form') || el.parentElement;
        return node ? node.innerText : '';
        """,
        element,
    ).strip()


def _answer_for_question(question: str, answers: dict, known_skills: set[str]) -> str | None:
    q = " ".join(question.lower().split())
    if not q:
        return None

    if "expected" in q and ("ctc" in q or "salary" in q or "compensation" in q):
        return str(answers.get("expected_ctc", "3600000"))
    if "current" in q and ("ctc" in q or "salary" in q or "compensation" in q):
        return str(answers.get("current_ctc", "2400000"))
    if "notice" in q:
        return str(answers.get("notice_period", "30 days"))
    if "preferred" in q and "location" in q:
        return ", ".join(answers.get("preferred_locations", []))
    if "current" in q and "location" in q:
        return str(answers.get("current_location", "Hyderabad"))
    if "relocat" in q:
        return str(answers.get("availability_to_relocate", "Yes"))
    if "work mode" in q or "employment type" in q or "job type" in q:
        return str(answers.get("work_mode_preference", "Full time"))
    if "total" in q and "experience" in q:
        return str(answers.get("total_experience_years", 4))
    if "experience" in q or "skill" in q or "technology" in q:
        if _mentions_known_skill(q, known_skills):
            return str(answers.get("relevant_skill_experience", "4 years"))
        return str(answers.get("missing_skill_answer", "NA"))

    return None


def _answer_radio_checkbox_groups(driver: webdriver.Chrome, answers: dict, known_skills: set[str], result: dict) -> bool:
    changed = False
    for option in driver.find_elements(By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']"):
        try:
            if not option.is_displayed() or option.is_selected():
                continue
            question = _question_text(driver, option)
            answer = _answer_for_question(question, answers, known_skills)
            if answer is None:
                continue
            answer_lower = answer.lower()
            option_text = _option_text(driver, option).lower()
            if answer_lower in option_text or option_text in answer_lower:
                driver.execute_script("arguments[0].click();", option)
                result["application_notes"].append(f"Selected option: {option_text[:80]}")
                changed = True
        except Exception as exc:
            result["application_notes"].append(f"Prompt option error: {exc}")
    return changed


def _answer_selects(driver: webdriver.Chrome, answers: dict, known_skills: set[str], result: dict) -> bool:
    changed = False
    for select in driver.find_elements(By.TAG_NAME, "select"):
        try:
            if not select.is_displayed():
                continue
            question = _question_text(driver, select)
            answer = _answer_for_question(question, answers, known_skills)
            if answer is None:
                continue
            options = select.find_elements(By.TAG_NAME, "option")
            for option in options:
                if answer.lower() in option.text.lower() or option.text.lower() in answer.lower():
                    option.click()
                    result["application_notes"].append(f"Selected dropdown: {option.text[:80]}")
                    changed = True
                    break
        except Exception as exc:
            result["application_notes"].append(f"Prompt dropdown error: {exc}")
    return changed


def _option_text(driver: webdriver.Chrome, option) -> str:
    option_id = option.get_attribute("id")
    if option_id:
        labels = driver.find_elements(By.CSS_SELECTOR, f"label[for='{option_id}']")
        label_text = " ".join(label.text for label in labels if label.text)
        if label_text:
            return label_text
    return driver.execute_script(
        """
        const el = arguments[0];
        const node = el.closest('label, li, div') || el.parentElement;
        return node ? node.innerText : '';
        """,
        option,
    ).strip()


def _click_next_submit(driver: webdriver.Chrome) -> bool:
    button_texts = [
        "Submit",
        "Save and apply",
        "Share My Interest",
        "Apply",
        "Next",
        "Continue",
        "Save",
    ]
    for text in button_texts:
        xpath = (
            f"//button[not(@disabled) and contains(translate(normalize-space(.), "
            f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
        )
        try:
            button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", button)
            return True
        except Exception:
            continue
    return False


def _known_skills(config: dict) -> set[str]:
    skills = set()
    for items in config.get("skill_categories", {}).values():
        for item in items:
            skills.add(item.lower())
    for alias, canonical in config.get("keyword_aliases", {}).items():
        skills.add(alias.lower())
        skills.add(canonical.lower())
    return skills


def _mentions_known_skill(question: str, known_skills: set[str]) -> bool:
    return any(skill and skill in question for skill in known_skills)
