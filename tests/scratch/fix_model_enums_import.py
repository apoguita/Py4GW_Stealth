import pathlib, re
p = pathlib.Path(r"C:\Users\Apo\Py4GW_Stealth\py4gw\enums_src\model_enums.py")
text = p.read_text(encoding="utf-8")
before = text.count("PySkill")
new = text.replace("import PySkill", "from .skill_names import GetSkillIDByName")
new, n = re.subn(r'PySkill\.Skill\("([^"]+)"\)\.id\.id', r'GetSkillIDByName("\1")', new)
p.write_text(new, encoding="utf-8")
print("PySkill occurrences before:", before, "call sites replaced:", n, "after:", new.count("PySkill"))
