import re
import shutil
import subprocess
from pathlib import Path

import yaml


BASE_TEX = Path("resumes/base.tex")
TMP_DIR = Path("tmp")
TMP_DIR.mkdir(exist_ok=True)


def _load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_skills_from_tex(tex: str) -> dict[str, list[str]]:
    r"""
    Finds the Technical Skills block and extracts:
    \item \textbf{Category:} skill1, skill2, ...
    """
    skills: dict[str, list[str]] = {}
    section_match = re.search(r"\\section\*\{Technical Skills\}(.*?)\\section\*\{", tex, re.DOTALL)
    if not section_match:
        return skills

    block = section_match.group(1)
    for match in re.finditer(r"\\item\s+\\textbf\{([^}]+?):\}\s+(.+)", block):
        category = _latex_unescape(match.group(1).strip())
        raw = match.group(2).strip()
        skills[category] = [_latex_unescape(skill.strip()) for skill in raw.split(",") if skill.strip()]

    return skills


def score_skills(
    skills: dict[str, list[str]],
    jd_keywords: list[str],
    aliases: dict[str, str],
) -> dict[str, list[str]]:
    """
    Reorders categories and skills by JD match strength.
    Nothing is added or removed.
    """
    jd_lower = {keyword.lower() for keyword in jd_keywords}

    def skill_matched(skill: str) -> bool:
        skill_lower = skill.lower()
        if skill_lower in jd_lower:
            return True
        for keyword, canonical in aliases.items():
            if keyword.lower() in jd_lower and canonical.lower() == skill_lower:
                return True
        return any(skill_lower in keyword or keyword in skill_lower for keyword in jd_lower)

    scored: list[tuple[int, str, list[str]]] = []
    for category, items in skills.items():
        matched = [skill for skill in items if skill_matched(skill)]
        unmatched = [skill for skill in items if not skill_matched(skill)]
        scored.append((len(matched), category, matched + unmatched))

    scored.sort(key=lambda item: -item[0])
    return {category: items for _, category, items in scored}


def rebuild_skills_section(reordered: dict[str, list[str]]) -> str:
    lines = [
        r"\section*{Technical Skills}",
        r"\begin{itemize}",
    ]
    for category, items in reordered.items():
        escaped_items = ", ".join(_latex_escape(item) for item in items)
        lines.append(f"    \\item \\textbf{{{_latex_escape(category)}:}} {escaped_items}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _latex_escape(value: str) -> str:
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
    }
    return "".join(replacements.get(char, char) for char in value)


def _latex_unescape(value: str) -> str:
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\$": "$",
        r"\#": "#",
        r"\_": "_",
    }
    for escaped, plain in replacements.items():
        value = value.replace(escaped, plain)
    return value


def rewrite_summary(tex: str, top_matched: list[str], config: dict) -> str:
    if not top_matched:
        return tex

    base = config.get("summary_base", "").strip()
    emphasis = ", ".join(top_matched[:5])
    new_summary = (
        f"{base} "
        f"Strong in {emphasis}, with a focus on scalable service development, "
        "production support, debugging, and troubleshooting."
    )

    return re.sub(
        r"(\\section\*\{Summary\}\n)(.*?)(\n\\section\*)",
        lambda match: match.group(1) + new_summary + "\n" + match.group(3),
        tex,
        flags=re.DOTALL,
    )


def tailor_resume(job: dict, jd_keywords: list[str]) -> Path:
    """
    Reads base.tex, reorders existing skills to match the JD, compiles to PDF,
    and returns the PDF path in tmp/.
    """
    config = _load_config()
    aliases = config.get("keyword_aliases", {})

    tex = BASE_TEX.read_text(encoding="utf-8")
    existing_skills = parse_skills_from_tex(tex)
    if not existing_skills:
        raise ValueError(
            "Could not parse Technical Skills from base.tex. "
            "Expected section header: \\section*{Technical Skills}."
        )

    reordered = score_skills(existing_skills, jd_keywords, aliases)
    jd_lower = {keyword.lower() for keyword in jd_keywords}
    top_matched = []
    for items in reordered.values():
        for skill in items:
            skill_lower = skill.lower()
            if any(skill_lower in keyword or keyword in skill_lower for keyword in jd_lower):
                top_matched.append(skill)
            if len(top_matched) >= 5:
                break
        if len(top_matched) >= 5:
            break

    tex = re.sub(
        r"\\section\*\{Technical Skills\}.*?\\end\{itemize\}",
        lambda _: rebuild_skills_section(reordered),
        tex,
        flags=re.DOTALL,
    )
    tex = rewrite_summary(tex, top_matched, config)

    slug = re.sub(r"\W+", "_", f"{job['company']}_{job['title']}")[:50] or "job"
    dest_tex = TMP_DIR / f"resume_{slug}.tex"
    dest_tex.write_text(tex, encoding="utf-8")

    pdf_path = _compile_tex(dest_tex)
    preferred_pages = config.get("resume", {}).get("preferred_pages", 1)
    page_count = _count_pdf_pages(pdf_path)
    job["resume_pages"] = page_count
    if page_count > preferred_pages:
        job["resume_warning"] = (
            f"Resume sent for apply is {page_count} pages "
            f"(preferred: {preferred_pages} page)."
        )
        print(f"     Warning: {job['resume_warning']}")

    print(f"     Resume compiled: {pdf_path.name}")
    return pdf_path


def _compile_tex(tex_path: Path) -> Path:
    if not shutil.which("pdflatex"):
        raise RuntimeError(
            "pdflatex is not installed or not on PATH. Install BasicTeX/MacTeX "
            "and restart the terminal, or run eval \"$(/usr/libexec/path_helper)\"."
        )

    result = subprocess.run(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory",
            str(tex_path.parent),
            str(tex_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    pdf = tex_path.with_suffix(".pdf")
    if result.returncode != 0 or not pdf.exists():
        log = tex_path.with_suffix(".log")
        hint = log.read_text(errors="ignore")[-1500:] if log.exists() else result.stdout[-1000:]
        raise RuntimeError(f"pdflatex failed for {tex_path.name}:\n{hint}")
    return pdf


def _count_pdf_pages(pdf_path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(pdf_path)).pages)


if __name__ == "__main__":
    tex_source = BASE_TEX.read_text(encoding="utf-8")
    skills = parse_skills_from_tex(tex_source)
    print("Parsed skills from base.tex:")
    for category, items in skills.items():
        print(f"  {category}: {items}")
