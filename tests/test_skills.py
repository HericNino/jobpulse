import pytest

from jobpulse.skills import canonical, guess_remote, guess_seniority, is_tech, match_skills


def test_aliases_map_to_one_canonical_name():
    assert canonical("postgres") == "PostgreSQL"
    assert canonical("  ReactJS ") == "React"
    assert canonical("unknown thing") is None


def test_match_handles_symbols_and_word_boundaries():
    text = "C++ and C# on .NET, plus Node.js. Experience with JavaScript and PostgreSQL."
    found = set(match_skills(text))
    assert {"C++", "C#", ".NET", "Node.js", "JavaScript", "PostgreSQL"} <= found
    assert "Java" not in found  # JavaScript must not count as Java
    assert "SQL" not in found  # only as part of PostgreSQL


def test_ambiguous_words_need_an_explicit_tag():
    text = "We go the extra mile, spring into action and love Ruby the dog."
    assert match_skills(text) == []
    assert match_skills(text, tags=["golang", "ruby"]) == ["Go", "Ruby"]


def test_react_native_does_not_imply_react():
    assert "React" not in match_skills("Mobile apps in React Native")
    assert {"React", "React Native"} <= set(match_skills("React for web, React Native for mobile"))


@pytest.mark.parametrize(
    ("title", "level"),
    [
        ("Senior Python Developer (m/w/d)", "senior"),
        ("Junior Frontend Engineer", "junior"),
        ("Staff Backend Engineer", "lead"),
        ("Software Engineering Intern", "intern"),
        ("Backend Engineer", "unknown"),
    ],
)
def test_guess_seniority(title, level):
    assert guess_seniority(title) == level


def test_guess_remote():
    assert guess_remote(True, "Engineer") == "remote"
    assert guess_remote(False, "Engineer", "Berlin (hybrid)") == "hybrid"
    assert guess_remote(False, "Engineer") == "onsite"
    assert guess_remote(None, "Engineer") == "unknown"


@pytest.mark.parametrize(
    ("title", "skills", "expected"),
    [
        ("Senior Backend Engineer", [], True),
        ("Développeur(euse) Java confirmé(e)", ["Java"], True),
        ("Softwareentwickler (m/w/d)", [], True),
        ("Account Executive, Early Stage - DACH", [], False),
        ("Partner Success Manager", ["SQL", "Testing"], False),  # weak signals don't count
        ("General Interest", ["Python", "C++", "PyTorch"], True),  # three concrete skills do
    ],
)
def test_is_tech(title, skills, expected):
    assert is_tech(title, skills) is expected


def test_plain_word_testing_is_not_a_skill():
    assert match_skills("Testing new markets and A/B testing campaigns") == []
    assert match_skills("Unit testing with pytest") == ["Testing"]
