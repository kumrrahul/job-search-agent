import yaml

from agent.resume import BASE_TEX, parse_skills_from_tex


def _load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_match_report(job: dict, jd_text: str, keywords: list[str]) -> dict:
    config = _load_config()
    resume_skills = _resume_skills(config)
    aliases = _alias_map(config)

    jd_skills = _jd_skills(job, keywords, aliases, resume_skills)
    resume_skill_names = _lower_set(resume_skills)
    matched = [skill for skill in jd_skills if skill.lower() in resume_skill_names]
    missing = [skill for skill in jd_skills if skill.lower() not in resume_skill_names]

    total_jd_skills = len(jd_skills)
    match_percent = round((len(matched) / max(1, total_jd_skills)) * 100)

    return {
        "match_percent": match_percent,
        "matched_skills": matched,
        "missing_skills": missing,
        "resume_skill_count": len(resume_skills),
        "jd_skill_count": total_jd_skills,
        "keyword_count": len(keywords),
        "summary": (
            f"{match_percent}% match: {len(matched)}/{total_jd_skills} JD skills "
            "are present in your resume."
        ),
    }


def _resume_skills(config: dict) -> list[str]:
    if BASE_TEX.exists():
        parsed = parse_skills_from_tex(BASE_TEX.read_text(encoding="utf-8"))
        skills = _unique(skill for items in parsed.values() for skill in items)
        if skills:
            return skills

    return _configured_skills(config)


def _jd_skills(
    job: dict,
    keywords: list[str],
    aliases: dict[str, str],
    resume_skills: list[str],
) -> list[str]:
    resume_display = {skill.lower(): skill for skill in resume_skills}
    raw_terms = [*job.get("tags", []), *keywords]

    skills = []
    seen = set()
    for term in raw_terms:
        canonical = _canonical_skill(term, aliases, resume_display)
        key = canonical.lower()
        if canonical and key not in seen:
            seen.add(key)
            skills.append(canonical)
    return skills


def _canonical_skill(
    term: str,
    aliases: dict[str, str],
    resume_display: dict[str, str],
) -> str:
    normalized = " ".join(str(term).lower().split())
    if not normalized:
        return ""
    if normalized in aliases:
        canonical = aliases[normalized]
        return resume_display.get(canonical.lower(), canonical)
    if normalized in resume_display:
        return resume_display[normalized]
    return str(term).strip()


def _alias_map(config: dict) -> dict[str, str]:
    return {
        " ".join(str(alias).lower().split()): str(canonical).strip()
        for alias, canonical in config.get("keyword_aliases", {}).items()
    }


def _lower_set(items: list[str]) -> set[str]:
    return {item.lower() for item in items}


def _unique(items) -> list[str]:
    seen = set()
    output = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output


def _configured_skills(config: dict) -> list[str]:
    skills = []
    for items in config.get("skill_categories", {}).values():
        for item in items:
            if item not in skills:
                skills.append(item)
    return skills


def _skill_in_text(skill: str, text: str, aliases: dict[str, str]) -> bool:
    skill_lower = skill.lower()
    if skill_lower in text:
        return True
    for alias, canonical in aliases.items():
        if canonical.lower() == skill_lower and alias.lower() in text:
            return True
    return False
