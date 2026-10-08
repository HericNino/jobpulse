"""Finding a stated salary in posting text, without a model.

Handles ranges and single figures in the usual formats ("€38k–45k", "65.000 – 80.000 €",
"$110,000 - $135,000", "45-55 K€", "PLN 22,000–28,000 per month", "15 € pro Stunde") and
works out the period from the words after the figure. A currency is required, so numbers
like "5 years", "50 %" or "401(k)" are never read as pay.
"""

from __future__ import annotations

import re
from typing import Literal, NamedTuple

Period = Literal["year", "month", "hour"]

_CURRENCY = r"(?:€|\$|£|EUR|USD|GBP|PLN|CAD|CHF|SEK|NOK|DKK|AUD)"
_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP"}
_NUMBER = r"\d{1,3}(?:[.,\s]\d{3})+|\d+(?:[.,]\d+)?"
_K = r"(?:\s?[kK](?![a-zA-Z]))?"


def _side(i: int) -> str:
    return rf"(?:(?P<c{i}>{_CURRENCY})\s?)?(?P<n{i}>{_NUMBER})(?P<k{i}>{_K})(?:\s?(?P<d{i}>{_CURRENCY}))?"


_RANGE = re.compile(rf"(?<![\w.,]){_side(1)}(?:\s*(?:-|–|—|to|bis|do|à)\s*{_side(2)})?(?![\w%])", re.IGNORECASE)

_HOUR = re.compile(r"^\W{0,3}(?:/\s?h\b|/\s?hour|per hour|an hour|hourly|pro stunde|/stunde|po satu|de l'heure|/heure)", re.I)
_MONTH = re.compile(
    r"^\W{0,3}(?:\S+\s){0,2}(?:/\s?month|per month|a month|monthly|/mo\b|mjesečno|mjesecno|monatlich|pro monat|par mois|mensuel)", re.I
)


class Salary(NamedTuple):
    min: int
    max: int
    currency: str
    period: Period


def _number(text: str, k: bool) -> float:
    grouped = re.fullmatch(r"\d{1,3}(?:[.,\s]\d{3})+", text)  # "65.000", "110,000", "2 500"
    value = float(re.sub(r"[.,\s]", "", text)) if grouped else float(text.replace(",", "."))
    return value * 1000 if k else value


def parse_salary(text: str | None) -> Salary | None:
    """The first stated salary in `text`, or None."""
    if not text:
        return None
    for m in _RANGE.finditer(text):
        currency = next((m.group(g) for g in ("c1", "d1", "c2", "d2") if m.group(g)), None)
        if not currency:
            continue
        k1, k2 = bool(m.group("k1").strip()), bool(m.group("k2") and m.group("k2").strip())
        low = _number(m.group("n1"), k1)
        high = _number(m.group("n2"), k2) if m.group("n2") else low
        # "90-110k", "45-55 K€": the k on one side applies to both
        if k2 and not k1 and low < 1000:
            low *= 1000
        if k1 and not k2 and m.group("n2") and high < 1000:
            high *= 1000
        if low > high:
            continue

        after = text[m.end() : m.end() + 40]
        if _HOUR.search(after):
            period: Period | None = "hour"
        elif _MONTH.search(after):
            period = "month"
        elif low >= 10_000:
            period = "year"
        else:
            period = None  # a small figure with no period ("$1,500 learning budget") isn't pay we can place
        if period is None:
            continue
        code = _SYMBOLS.get(currency, currency.upper())
        return Salary(round(low), round(high), code, period)
    return None
