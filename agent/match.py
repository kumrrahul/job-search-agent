import yaml


def _load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_match_report(job: dict, jd_text: str, keywords: list[str]) -> dict:
    config = _load_config()
    skills = _configured_skills(config)
    aliases = config.get("keyword_aliases", {})
    text = " ".join([jd_text, job.get("title", ""), job.get("snippet", "")]).lower()

    matched = []
    missing = []
    for skill in skills:
        if _skill_in_text(skill, text, aliases):
            matched.append(skill)
        else:
            missing.append(skill)

    total = len(skills) or 1
    skill_score = round((len(matched) / total) * 100)
    keyword_bonus = min(len(keywords), 10)
    match_percent = min(100, round((skill_score * 0.85) + keyword_bonus))

    return {
        "match_percent": match_percent,
        "matched_skills": matched,
        "missing_skills": missing,
        "keyword_count": len(keywords),
        "summary": f"{match_percent}% match: {len(matched)}/{total} configured resume skills found in JD.",
    }


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
