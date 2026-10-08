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
_TAG_ONLY = {"go", "ts", "js", "node", "ml", "spring", "swift", "rust", "ruby", "spark", "containers"}


def _pattern(alias: str) -> re.Pattern[str]:
    # \b fails next to symbols ("c++", ".net"), so use explicit look-arounds
    return re.compile(rf"(?<![\w.+#]){re.escape(alias)}(?![\w+#])", re.IGNORECASE)


_TEXT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (name, _pattern(alias)) for name, (_, aliases) in SKILLS.items() for alias in [name.lower(), *aliases] if alias not in _TAG_ONLY
]
_ALIASES: dict[str, str] = {alias: name for name, (_, aliases) in SKILLS.items() for alias in [name.lower(), *aliases]}


def canonical(skill: str) -> str | None:
    """Map any alias (any case) to its canonical name, or None if unknown."""
    return _ALIASES.get(skill.strip().lower())


def match_skills(text: str, tags: tuple[str, ...] | list[str] = ()) -> list[str]:
    found = {name for name, pattern in _TEXT_PATTERNS if pattern.search(text)}
    found.update(c for tag in tags if (c := canonical(tag)))
    # "React Native" mentions also contain "React"; only count React if it appears on its own
    if "React Native" in found and "React" in found and not re.search(r"react(?!\s+native)", text, re.IGNORECASE):
        found.discard("React")
    return sorted(found)


_SENIORITY_RULES: list[tuple[Seniority, re.Pattern[str]]] = [
    ("intern", re.compile(r"\b(intern|internship|trainee|praktikant|student)\b", re.I)),
    ("lead", re.compile(r"\b(lead|principal|staff|head of|architect|director)\b", re.I)),
    ("senior", re.compile(r"\b(senior|sr\.?)\b", re.I)),
    ("junior", re.compile(r"\b(junior|jr\.?|entry[- ]level|graduate)\b", re.I)),
    ("mid", re.compile(r"\b(mid|medior|intermediate)\b", re.I)),
]


def guess_seniority(title: str) -> Seniority:
    for level, pattern in _SENIORITY_RULES:
        if pattern.search(title):
            return level
    return "unknown"


def guess_remote(flag: bool | None, *texts: str) -> Remote:
    joined = " ".join(texts).lower()
    if "hybrid" in joined:
        return "hybrid"
    if flag or re.search(r"\b(fully remote|remote[- ]first|100% remote|work from anywhere)\b", joined):
        return "remote"
    if flag is False:
        return "onsite"
    return "unknown"
