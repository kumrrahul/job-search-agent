#!/usr/bin/env python3
"""
Naukri Job Application Agent — CLI entry point

Usage:
  python run.py                      # full run (scrape → tailor → apply → email)
  python run.py --dry-run            # scrape + tailor only, no apply, no email
  python run.py --dry-run --limit 2  # test with 2 jobs
  python run.py --check              # validate local setup
  python run.py --no-email           # apply but skip email
  python run.py --limit 5            # cap at 5 applications
"""
import argparse
import traceback
from datetime import datetime
from pathlib import Path
import shutil
import sys
from agent.checks     import run_setup_check
from agent            import db


def main():
    # Initialize database
    db.init_db()

    parser = argparse.ArgumentParser(description="Naukri Job Application Agent")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Tailor resumes but do not apply or email")
    parser.add_argument("--no-email", action="store_true",
                        help="Apply but skip sending the email summary")
    parser.add_argument("--limit",    type=int, default=None,
                        help="Max number of jobs to process")
    parser.add_argument("--days",     type=int, default=None,
                        help="How many days back to look for jobs")
    parser.add_argument("--check",    action="store_true",
                        help="Validate local setup and exit")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if run_setup_check() else 1)

    import yaml

    from agent.scraper    import fetch_jobs, fetch_jd, extract_keywords
    from agent.resume     import tailor_resume
    from agent.applicator import build_driver, login, apply_to_job, upload_profile_resume
    from agent.reporter   import send_summary
    from agent.match      import build_match_report

    # Load limits from config (CLI args override config)
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    limits   = cfg.get("limits", {})
    max_jobs = args.limit or limits.get("max_jobs", 15)
    days     = args.days  or limits.get("days_back", 7)
    delay    = limits.get("apply_delay_seconds", 3)
    min_match = cfg.get("matching", {}).get("min_apply_match_percent", 50)

    print("=" * 55)
    print("  Naukri Job Application Agent")
    print(f"  Mode   : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Limit  : {max_jobs} jobs  |  Last {days} days")
    print("=" * 55)

    # ── Step 1: Scrape matching jobs ─────────────────────────────
    print("\n[1/4] Scraping Naukri for matching jobs...")
    jobs = fetch_jobs(days=days, max_jobs=max_jobs)
    print(f"  Total jobs found: {len(jobs)}")

    if not jobs:
        print("  No jobs found. Exiting.")
        return

    # ── Step 2: Tailor resume for each job ───────────────────────
    print("\n[2/4] Tailoring resumes...")
    results = []

    for i, job in enumerate(jobs, 1):
        print(f"\n  [{i}/{len(jobs)}] {job['title']} @ {job['company']}")
        try:
            jd_text  = fetch_jd(job["url"])
            keywords = extract_keywords(jd_text)
            job["match_report"] = build_match_report(job, jd_text, keywords)
            print(f"     Matched keywords: {keywords[:8]}")
            print(f"     ATS match: {job['match_report']['match_percent']}%")

            if job["match_report"]["match_percent"] < min_match:
                job["pdf"] = ""
                job["status"] = "skipped_low_match"
                job["error"] = (
                    f"ATS match {job['match_report']['match_percent']}% is below "
                    f"minimum {min_match}%."
                )
                db.update_job_status(job["url"], job["title"], job["company"], job["status"])
                results.append(job)
                print(f"     Skipped: {job['error']}")
                continue

            pdf_path = tailor_resume(job, keywords)
            job["pdf"] = str(pdf_path)
        except Exception as e:
            print(f"     Resume tailor failed: {e}")
            job["pdf"]    = ""
            job["status"] = "failed"
            job["error"]  = str(e)
            results.append(job)
            continue

        if args.dry_run:
            job["status"] = "dry_run"
            job["error"]  = ""
            results.append(job)
            print(f"     [dry-run] Resume saved: {job['pdf']}")
        else:
            results.append(job)   # will be updated in step 3

    if args.dry_run:
        print("\n[DRY RUN] Skipping application and email steps.")
        print("\nTailored resumes written to tmp/:")
        for r in results:
            if r.get("pdf"):
                print(f"  {r['pdf']}")
        return

    # ── Step 3: Apply ────────────────────────────────────────────
    print("\n[3/4] Applying to jobs...")
    driver = build_driver()
    login(driver)

    import time
    for r in results:
        if r.get("status") in {"failed", "skipped_low_match"} or not r.get("pdf"):
            continue
        
        pdf_path = Path(r["pdf"])
        # Rename to resume_<date>.pdf for profile upload
        date_str = datetime.now().strftime("%Y%m%d")
        new_pdf_name = f"resume_{date_str}.pdf"
        new_pdf_path = pdf_path.parent / new_pdf_name
        shutil.copy(pdf_path, new_pdf_path)
        r["pdf"] = str(new_pdf_path)

        print(f"\n  Applying: {r['title']} @ {r['company']}")
        
        # Step 3.1: Upload tailored resume to profile
        upload_profile_resume(driver, new_pdf_path)
        
        # Step 3.2: Apply
        result = apply_to_job(r, new_pdf_path, driver)
        r.update(result)
        
        # Update DB status
        db.update_job_status(r["url"], r["title"], r["company"], r["status"])
        
        print(f"  Status  : {r['status']}")
        if r.get("error"):
            print(f"  Error   : {r['error']}")
        time.sleep(delay)

    driver.quit()

    # ── Step 4: Email summary ────────────────────────────────────
    if args.no_email:
        print("\n[4/4] Skipping email (--no-email flag set).")
    else:
        print("\n[4/4] Sending email summary...")
        try:
            send_summary(results)
        except Exception as e:
            print(f"  Email failed: {e}")
            traceback.print_exc()

    # ── Final summary ────────────────────────────────────────────
    applied  = sum(1 for r in results if r["status"] == "applied")
    failed   = sum(1 for r in results if r["status"] == "failed")
    skipped  = sum(1 for r in results if r["status"] in {"already_applied", "skipped_external"})
    low_match = sum(1 for r in results if r["status"] == "skipped_low_match")

    print("\n" + "=" * 55)
    print(f"  Done.  Applied: {applied}  |  Failed: {failed}  |  Skipped: {skipped}  |  Low match: {low_match}")
    print("=" * 55)


if __name__ == "__main__":
    main()
