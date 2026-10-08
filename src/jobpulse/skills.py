"""Skill vocabulary and a keyword matcher.

Every skill has one canonical name and a few aliases. Reports only ever use
canonical names, so "Postgres", "PostgreSQL" and "psql" count as one skill.
The matcher is the free, offline baseline; Claude's analysis (extract.py) is
asked to answer in the same vocabulary.
"""

from __future__ import annotations

import re

from .models import Remote, Seniority

# canonical name -> (category, aliases)
SKILLS: dict[str, tuple[str, list[str]]] = {
    # languages
    "Python": ("Languages", ["python"]),
    "JavaScript": ("Languages", ["javascript", "js", "ecmascript"]),
    "TypeScript": ("Languages", ["typescript", "ts"]),
    "Java": ("Languages", ["java"]),
    "Kotlin": ("Languages", ["kotlin"]),
    "C#": ("Languages", ["c#", "csharp"]),
    "C++": ("Languages", ["c++", "cpp"]),
    "Go": ("Languages", ["golang", "go lang"]),
    "Rust": ("Languages", ["rust"]),
    "PHP": ("Languages", ["php"]),
    "Ruby": ("Languages", ["ruby"]),
    "Swift": ("Languages", ["swift"]),
    "Scala": ("Languages", ["scala"]),
    "SQL": ("Languages", ["sql"]),
    # frontend
    "React": ("Frontend", ["react", "react.js", "reactjs"]),
    "Next.js": ("Frontend", ["next.js", "nextjs"]),
    "Vue": ("Frontend", ["vue", "vue.js", "vuejs", "nuxt"]),
    "Angular": ("Frontend", ["angular"]),
    "Svelte": ("Frontend", ["svelte", "sveltekit"]),
    "CSS": ("Frontend", ["css", "sass", "scss", "tailwind", "tailwindcss"]),
    "React Native": ("Mobile", ["react native"]),
    "Flutter": ("Mobile", ["flutter", "dart"]),
    "iOS": ("Mobile", ["ios"]),
    "Android": ("Mobile", ["android"]),
    # backend
    "Node.js": ("Backend", ["node.js", "nodejs", "node"]),
    "Django": ("Backend", ["django"]),
    "FastAPI": ("Backend", ["fastapi"]),
    "Flask": ("Backend", ["flask"]),
    "Spring": ("Backend", ["spring", "spring boot"]),
    ".NET": ("Backend", [".net", "dotnet", "asp.net"]),
    "Rails": ("Backend", ["rails", "ruby on rails"]),
    "Laravel": ("Backend", ["laravel"]),
    "GraphQL": ("Backend", ["graphql"]),
    "REST APIs": ("Backend", ["rest api", "rest apis", "restful"]),
    "Microservices": ("Backend", ["microservices", "microservice"]),
    # data
    "PostgreSQL": ("Data", ["postgresql", "postgres", "psql"]),
    "MySQL": ("Data", ["mysql", "mariadb"]),
    "MongoDB": ("Data", ["mongodb", "mongo"]),
    "Redis": ("Data", ["redis"]),
    "Elasticsearch": ("Data", ["elasticsearch", "opensearch"]),
    "Kafka": ("Data", ["kafka"]),
    "Spark": ("Data", ["spark", "pyspark"]),
    "Airflow": ("Data", ["airflow"]),
    "dbt": ("Data", ["dbt"]),
    "Snowflake": ("Data", ["snowflake"]),
    "Pandas": ("Data", ["pandas"]),
    "Power BI": ("Data", ["power bi", "powerbi"]),
    "Tableau": ("Data", ["tableau"]),
    # cloud & ops
    "AWS": ("Cloud & DevOps", ["aws", "amazon web services"]),
    "Azure": ("Cloud & DevOps", ["azure"]),
    "GCP": ("Cloud & DevOps", ["gcp", "google cloud"]),
    "Docker": ("Cloud & DevOps", ["docker", "containers"]),
    "Kubernetes": ("Cloud & DevOps", ["kubernetes", "k8s"]),
    "Terraform": ("Cloud & DevOps", ["terraform"]),
    "CI/CD": ("Cloud & DevOps", ["ci/cd", "continuous integration", "github actions", "gitlab ci", "jenkins"]),
    "Linux": ("Cloud & DevOps", ["linux"]),
    # AI
    "Machine Learning": ("AI", ["machine learning", "ml"]),
    "LLMs": ("AI", ["llm", "llms", "large language model", "large language models", "generative ai", "genai"]),
    "PyTorch": ("AI", ["pytorch"]),
    "TensorFlow": ("AI", ["tensorflow"]),
    # practice
    "Testing": ("Practice", ["unit testing", "test automation", "tdd", "jest", "pytest", "cypress", "playwright"]),
    "Agile": ("Practice", ["agile", "scrum", "kanban"]),
    "Git": ("Practice", ["git"]),
}

CATEGORY = {name: category for name, (category, _) in SKILLS.items()}

# Aliases that are ordinary words or too ambiguous to match in free text.
# They still count when a source tags a posting with them explicitly.
_TAG_ONLY = {"go", "ts", "js", "node", "ml", "spring", "swift", "rust", "ruby", "spark", "containers", "testing"}


# Croatian (and other inflected languages) add endings: "u Reactu", "s TypeScriptom", "u Javi".
_ENDINGS = r"(?:u|om|a|e|i|em|ima|ovi|ove|ju)?"


def _pattern(alias: str) -> re.Pattern[str]:
    # \b fails next to symbols ("c++", ".net"), so use explicit look-arounds
    body = re.escape(alias)
    if len(alias) >= 4 and alias[-1].isalpha():
        # words ending in -a drop it before the ending ("Kafka" -> "Kafkom")
        body = re.escape(alias[:-1]) + r"(?:a|e|i|u|om|ama)" if alias.endswith("a") else body + _ENDINGS
    return re.compile(rf"(?<![\w.+#]){body}(?![\w+#])", re.IGNORECASE)


_TEXT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (name, _pattern(alias)) for name, (_, aliases) in SKILLS.items() for alias in [name.lower(), *aliases] if alias not in _TAG_ONLY
]
_ALIASES: dict[str, str] = {alias: name for name, (_, aliases) in SKILLS.items() for alias in [name.lower(), *aliases]}


def canonical(skill: str) -> str | None:
    """Map any alias (any case) to its canonical name, or None if unknown."""
    return _ALIASES.get(skill.strip().lower())


# Ambiguous names count in free text only when written as a name in a technical context:
# "services in Go", "with Rust and C++" - but not "you'll go on-call" or "spring cleaning".
_NAMED_IN_CONTEXT = re.compile(r"(?:\b(?:in|with|using|and|or)|[,/])\s+(Go|Rust|Ruby|Swift|Spark)\b(?![-'])")


def match_skills(text: str, tags: tuple[str, ...] | list[str] = ()) -> list[str]:
    # "Machine-Learning-Modelle" -> "Machine Learning Modelle", so multi-word names still match
    text = re.sub(r"(?<=[^\W\d_])-(?=[^\W\d_])", " ", text)
    found = {name for name, pattern in _TEXT_PATTERNS if pattern.search(text)}
    found.update(m.group(1) for m in _NAMED_IN_CONTEXT.finditer(text))
    found.update(c for tag in tags if (c := canonical(tag)))
    # "React Native" mentions also contain "React"; only count React if it appears on its own
    if "React Native" in found and "React" in found and not re.search(r"react(?!\s+native)", text, re.IGNORECASE):
        found.discard("React")
    return sorted(found)


_SENIORITY_RULES: list[tuple[Seniority, re.Pattern[str]]] = [
    ("intern", re.compile(r"\b(intern|internship|trainee|praktikant|student|werkstudent\w*|praksa)\b", re.I)),
    ("lead", re.compile(r"\b(lead|principal|staff|head of|architect|director)\b", re.I)),
    ("senior", re.compile(r"\b(senior|sr\.?)\b", re.I)),
    ("junior", re.compile(r"\b(junior|jr\.?|entry[- ]level|graduate)\b", re.I)),
    ("mid", re.compile(r"\b(mid|medior|intermediate)\b", re.I)),
]

_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
# "5+ years", "3-5 years", "minimalno 4 godine", "3 ans d'expérience", "2 Jahre Erfahrung", "Seven years"
_YEARS = re.compile(
    r"\b(\d{1,2}|" + "|".join(_WORD_NUMBERS) + r")\s*\+?\s*(?:(?:-|–|to|do|bis)\s*\d{1,2}\s*\+?\s*)?"
    r"(?:years?|yrs|jahre?n?|ans|godin[ae]?)\b",
    re.IGNORECASE,
)
_JUNIOR_TEXT = re.compile(
    r"berufseinsteiger|entry[- ]level|no experience (?:required|needed)|iskustvo nije nužno|graduate programme|graduate program", re.I
)


def _seniority_from_years(years: int) -> Seniority:
    return "junior" if years < 2 else "mid" if years < 5 else "senior"


_TECH_TITLE = re.compile(
    r"(engineer|developer|d[eé]velopp|entwickl|programm|devops|\bsre\b|\bdata\b|software|front[- ]?end|back[- ]?end|full[- ]?stack"
    r"|architect|machine learning|\bml\b|\bai\b|\bki\b|cloud|security|\bqa\b|\btest|administrat|\bit[- ]|informati"
    r"|platform|mobile|\bios\b|android|\bweb|scientist|analyst|cyber|network|netzwerk|database|\bsystem)",
    re.IGNORECASE,
)
# skills that show up in plenty of non-engineering postings, so they don't count as evidence
_WEAK_SIGNALS = {"Testing", "Agile", "Git", "LLMs", "Machine Learning", "Power BI", "Tableau", "SQL"}


def is_tech(title: str, skills: list[str]) -> bool:
    """Whether a posting is a tech role: a tech-sounding title, or at least three concrete technical skills."""
    return bool(_TECH_TITLE.search(title)) or len([s for s in skills if s not in _WEAK_SIGNALS]) >= 3


def guess_seniority(title: str, description: str = "") -> Seniority:
    """From the title first; failing that, from experience stated in the text ("5+ years" -> senior)."""
    for level, pattern in _SENIORITY_RULES:
        if pattern.search(title):
            return level
    if _JUNIOR_TEXT.search(description):
        return "junior"
    if m := _YEARS.search(description):
        value = m.group(1).lower()
        return _seniority_from_years(int(value) if value.isdigit() else _WORD_NUMBERS[value])
    return "unknown"


_HYBRID = re.compile(
    r"hybrid|hybride|hibrid|"
    r"\b\d\s*(?:days?|tage?n?|dana|jours?)\b.{0,30}?(?:office|büro|uredu?|bureau)|"
    r"(?:two|three|four|\d) (?:office days|days (?:a|per) week in)|"
    r"télétravail\s+\d|rad od kuće\s+\d|remote[- ]anteil\s*\d+\s*%",
    re.IGNORECASE,
)
_REMOTE = re.compile(
    r"\b(?:fully remote|remote[- ]first|100\s*%\s*(?:remote|télétravail)|work from anywhere|remote within|remote contract)\b"
    r"|\bremote\b(?![- ]anteil)",
    re.IGNORECASE,
)
_ONSITE = re.compile(
    r"on-site|onsite|office-based|in-person|in person|vor ort|im büro|u uredu|five days a week|rad u uredu|sur site",
    re.IGNORECASE,
)


def guess_remote(flag: bool | None, *texts: str) -> Remote:
    """Hybrid wins over remote, remote over on-site; the source's own flag decides when the text says nothing."""
    joined = " ".join(texts)
    if _HYBRID.search(joined):
        return "hybrid"
    if flag or _REMOTE.search(joined):
        return "remote"
    if flag is False or _ONSITE.search(joined):
        return "onsite"
    return "unknown"
