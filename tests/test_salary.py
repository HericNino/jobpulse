import pytest

from jobpulse.salary import Salary, parse_salary


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Salary €38k–45k.", Salary(38000, 45000, "EUR", "year")),
        ("Gehalt: 65.000 – 80.000 € brutto im Jahr.", Salary(65000, 80000, "EUR", "year")),
        ("Pay: $110,000 - $135,000 per year.", Salary(110000, 135000, "USD", "year")),
        ("Salaire : 45-55 K€ brut annuel.", Salary(45000, 55000, "EUR", "year")),
        ("Salary 90-110k EUR.", Salary(90000, 110000, "EUR", "year")),
        ("Rate: €70–85/hour.", Salary(70, 85, "EUR", "hour")),
        ("Remote contract. $4,000–$5,000/month.", Salary(4000, 5000, "USD", "month")),
        ("PLN 22,000–28,000 per month (B2B).", Salary(22000, 28000, "PLN", "month")),
        ("Plaća 2.200 – 2.800 EUR neto mjesečno.", Salary(2200, 2800, "EUR", "month")),
        ("Hybrid möglich. 15 € pro Stunde.", Salary(15, 15, "EUR", "hour")),
        ("Gehalt: 52.000 € p.a.", Salary(52000, 52000, "EUR", "year")),
        ("Hybrid. £95k–£115k.", Salary(95000, 115000, "GBP", "year")),
        ("€80,000 to €95,000.", Salary(80000, 95000, "EUR", "year")),
    ],
)
def test_parses_common_formats(text, expected):
    assert parse_salary(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "We offer a competitive salary and learning budget.",
        "Equity: 0.5–1%.",
        "401(k) matching and a $1,500 learning budget.",
        "5+ years of experience, 25 days off.",
        "Remote-Anteil 50 %.",
        "",
        None,
    ],
)
def test_ignores_things_that_are_not_pay(text):
    assert parse_salary(text) is None
