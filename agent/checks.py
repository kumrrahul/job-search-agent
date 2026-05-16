import importlib.util
import os
import shutil
from pathlib import Path


REQUIRED_ENV_VARS = [
    "NAUKRI_EMAIL",
    "NAUKRI_PASSWORD",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASS",
    "NOTIFY_TO",
]

REQUIRED_PACKAGES = [
    "bs4",
    "dotenv",
    "lxml",
    "pypdf",
    "selenium",
    "yaml",
]


def run_setup_check() -> bool:
    """Validates local setup without logging credentials or launching Selenium."""
    _load_dotenv_file(Path(".env"))
    checks: list[tuple[str, bool, str]] = []

    checks.extend(_file_checks())
    checks.extend(_config_checks())
    checks.extend(_env_checks())
    checks.extend(_package_checks())
    checks.extend(_tool_checks())

    print("\nSetup check")
    print("=" * 55)
    for label, ok, detail in checks:
        marker = "OK " if ok else "ERR"
        suffix = f" - {detail}" if detail else ""
        print(f"[{marker}] {label}{suffix}")

    if any(not ok for _, ok, _ in checks):
        print("\nFix the failed checks above, then rerun: python run.py --check")
        return False

    print("\nAll setup checks passed.")
    return True


def _file_checks() -> list[tuple[str, bool, str]]:
    required_files = [
        Path("config.yaml"),
        Path("resumes/base.tex"),
        Path(".env.example"),
    ]
    return [
        (f"File exists: {path}", path.exists(), "" if path.exists() else "missing")
        for path in required_files
    ]


def _config_checks() -> list[tuple[str, bool, str]]:
    config_path = Path("config.yaml")
    if not config_path.exists():
        return [("Config can be parsed", False, "config.yaml is missing")]
    if importlib.util.find_spec("yaml") is None:
        return [("Config can be parsed", False, "pyyaml is not installed")]

    try:
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [("Config can be parsed", False, str(exc))]

    return [
        ("Config can be parsed", True, ""),
        (
            "Config has role aliases",
            bool(config.get("role_aliases")),
            "" if config.get("role_aliases") else "role_aliases is empty",
        ),
        (
            "Config has skill categories",
            bool(config.get("skill_categories")),
            "" if config.get("skill_categories") else "skill_categories is empty",
        ),
    ]


def _env_checks() -> list[tuple[str, bool, str]]:
    env_path = Path(".env")
    checks = [
        (
            "Environment file .env",
            env_path.exists(),
            "" if env_path.exists() else "copy .env.example to .env and fill values",
        )
    ]
    for key in REQUIRED_ENV_VARS:
        value = os.getenv(key)
        checks.append((f"Env var {key}", bool(value), "" if value else "missing or empty"))
    return checks


def _package_checks() -> list[tuple[str, bool, str]]:
    checks = []
    for package in REQUIRED_PACKAGES:
        ok = importlib.util.find_spec(package) is not None
        checks.append((f"Python package {package}", ok, "" if ok else "not installed"))
    return checks


def _tool_checks() -> list[tuple[str, bool, str]]:
    pdflatex = shutil.which("pdflatex")
    chrome = _find_chrome()
    return [
        (
            "Tool pdflatex",
            bool(pdflatex),
            pdflatex or "install BasicTeX/MacTeX and refresh PATH",
        ),
        (
            "Chrome browser",
            bool(chrome),
            chrome or "install Google Chrome or Chromium for Selenium",
        ),
    ]


def _find_chrome() -> str | None:
    for binary in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
        path = shutil.which(binary)
        if path:
            return path

    for path in [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]:
        if Path(path).exists():
            return path

    return None


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
