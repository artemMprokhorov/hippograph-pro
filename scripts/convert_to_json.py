#!/usr/bin/env python3
import json
from pathlib import Path

def parse_skill_md(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except:
        return None
    
    skill_name = path.parent.name
    
    if "security" in str(path).lower() or "audit" in skill_name:
        category = "security-critical"
    elif "android" in str(path).lower() or "mobile" in skill_name:
        category = "development"
    elif "anthropic" in str(path).lower() or "mcp" in skill_name:
        category = "ml-architecture"
    else:
        category = "development"
    
    # Extract first meaningful paragraph
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    desc_lines = []
    for line in lines:
        if not line.startswith("#") and len(line) > 20:
            desc_lines.append(line)
            if len(desc_lines) >= 2:
                break
    
    desc_text = " ".join(desc_lines)[:200] if desc_lines else f"Skill: {skill_name}"
    
    return {
        "name": skill_name,
        "purpose": desc_text,
        "category": category,
        "intensity": 7,
        "tags": [skill_name.split("-")[0]] if "-" in skill_name else [skill_name]
    }

skills_dir = Path("./skills")
skill_files = list(skills_dir.rglob("SKILL.md"))

print(f"Found {len(skill_files)} skills")

skills = []
for path in skill_files:
    skill = parse_skill_md(path)
    if skill:
        skills.append(skill)
        name = skill["name"]
        print(f"  ✓ {name}")

output = skills_dir / "all_skills.json"
with open(output, "w") as f:
    json.dump(skills, f, indent=2)

print(f"\n✅ Saved {len(skills)} skills to all_skills.json")
