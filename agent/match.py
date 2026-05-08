import yaml


def _load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_match_report(job: dict, jd_text: str, keywords: list[str]) -> dict:
    config = _load_config()
    my_skills = {s.lower() for s in _configured_skills(config)}
    aliases = {k.lower(): v.lower() for k, v in config.get("keyword_aliases", {}).items()}
    
    # Required skills = tags from job card + keywords found in JD
    # We use tags as the primary source of 'required' skills
    required_skills = set(job.get("tags", []))
    for kw in keywords:
        required_skills.add(kw.lower())

    matched = []
    for req in required_skills:
        # Does my profile have this required skill (or its canonical form)?
        if req in my_skills:
            matched.append(req)
        elif req in aliases and aliases[req] in my_skills:
            matched.append(aliases[req])

    total_req = len(required_skills)
    match_percent = round((len(matched) / max(1, total_req)) * 100)

    return {
        "match_percent": match_percent,
        "matched_skills": list(set(matched)),
        "missing_skills": list(required_skills - set(matched)),
        "keyword_count": len(keywords),
        "summary": f"{match_percent}% match: {len(matched)}/{total_req} skills required by JD are in your profile.",
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
