"""
date_resolver.py — Natural language date resolution for a HISTORICAL dataset.

Key design rule (spec §9, §14):
  Month names without a year are resolved using the DATASET year, NOT the
  computer's current date.  The dataset year is derived from db_min.

Supported expressions:
  • Month names: "April", "May", "in April", "during May", "entire April"
  • "This month" / "current month" / "last month" / "previous month"
    → resolved against dataset year/months, NOT today
  • "Complete Dataset", "Complete Date Range", "Entire Dataset",
    "Full Database", "All Available Data"  → full db_min..db_max
  • Explicit dates: YYYY-MM-DD, DD/MM/YYYY, D/M/YYYY, DD-MM-YYYY
"""

import re
import datetime
import calendar

# Month name → number
MONTH_NAMES: dict[str, int] = {
    "january": 1,  "jan": 1,
    "february": 2, "feb": 2,
    "march": 3,    "mar": 3,
    "april": 4,    "apr": 4,
    "may": 5,
    "june": 6,     "jun": 6,
    "july": 7,     "jul": 7,
    "august": 8,   "aug": 8,
    "september": 9,"sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11,"nov": 11,
    "december": 12,"dec": 12,
}

COMPLETE_DATASET_PATTERNS = [
    r"\bcomplete\s+(date\s+)?range\b",
    r"\bentire\s+(date\s+)?range\b",
    r"\ball\s+(available\s+)?data\b",
    r"\bfull\s+(database|range|data)\b",
    r"\bcomplete\s+database\b",
    r"\bentire\s+dataset\b",
    r"\bcomplete\s+dataset\b",
    r"\ball\s+dates?\b",
    r"\b__complete_range__\b",
]


def _dataset_year(db_min: str) -> int:
    """Extract the year from the dataset start date string (YYYY-MM-DD)."""
    return int(db_min[:4])


def _last_day(year: int, month: int) -> datetime.date:
    """Return the last calendar day of the given year/month."""
    return datetime.date(year, month, calendar.monthrange(year, month)[1])


def detect_invalid_date_strings(text: str) -> str | None:
    """
    Scan text for date-like tokens that LOOK like dates but are invalid
    (impossible calendar values, wrong format, etc.).

    Returns an error message string if any invalid date-like token is found,
    or None if everything looks fine.

    This must be called BEFORE resolve_dates / _extract_explicit_dates so that
    bad input is rejected immediately rather than silently ignored.
    """
    # Patterns that LOOK like dates:
    #   YYYY-MM-DD  or  YYYY/MM/DD
    #   DD-MM-YYYY  or  DD/MM/YYYY  or  D/M/YYYY
    #   Also catches obvious garbage like 32-13-2026 or abc-xyz

    candidate_patterns = [
        # ISO-ish: four-digit year first
        (r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b', 'ymd'),
        # Day-first: four-digit year last
        (r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', 'dmy'),
    ]

    errors = []
    for pattern, order in candidate_patterns:
        for m in re.finditer(pattern, text):
            raw = m.group(0)
            try:
                if order == 'ymd':
                    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                else:  # dmy
                    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))

                # Attempt to construct the date — this raises ValueError for
                # impossible calendar dates (Feb 30, month 13, day 32, etc.)
                datetime.date(y, mo, d)

            except (ValueError, OverflowError):
                errors.append(raw)

    if errors:
        bad = ", ".join(f'"{e}"' for e in errors)
        return (
            f"Invalid date: {bad}.\n\n"
            "Please enter a valid date in the format YYYY-MM-DD or select a "
            "valid date range."
        )

    return None


def _extract_explicit_dates(text: str) -> list[str]:
    """Extract and normalise all explicit dates in text → YYYY-MM-DD list."""
    results = []

    # YYYY-MM-DD
    for m in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            results.append(str(datetime.date(y, mo, d)))
        except ValueError:
            pass

    # DD/MM/YYYY or D/M/YYYY or DD-MM-YYYY
    for m in re.finditer(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b", text):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            results.append(str(datetime.date(y, mo, d)))
        except ValueError:
            pass

    return results


def resolve_dates(text: str, db_min: str, db_max: str) -> dict | None:
    """
    Try to resolve natural-language date expressions in `text`.

    Returns {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"} or None.

    Months without an explicit year are resolved using the DATASET year
    (derived from db_min), never the computer's current date.
    """
    text_l = text.lower().strip()
    ds_year = _dataset_year(db_min)   # e.g. 2026

    # 1. Complete dataset keywords
    for pat in COMPLETE_DATASET_PATTERNS:
        if re.search(pat, text_l):
            return {"start_date": db_min, "end_date": db_max}

    # 2. "This month" / "current month"
    #    → the month that contains db_min (i.e. the first month of the dataset)
    if re.search(r"\b(this|current)\s+month\b", text_l):
        db_start = datetime.date.fromisoformat(db_min)
        first = db_start.replace(day=1)
        last  = _last_day(first.year, first.month)
        return {"start_date": str(first), "end_date": str(last)}

    # 3. "Last month" / "previous month"
    #    → the month before the dataset's start month
    if re.search(r"\b(last|previous)\s+month\b", text_l):
        db_start = datetime.date.fromisoformat(db_min)
        first_db = db_start.replace(day=1)
        last_prev_end   = first_db - datetime.timedelta(days=1)
        last_prev_start = last_prev_end.replace(day=1)
        return {"start_date": str(last_prev_start), "end_date": str(last_prev_end)}

    # 4. Named month with EXPLICIT year: "April 2026", "April 2027"
    #    Pattern: <month_name> <4-digit-year>  or  <4-digit-year>-<month>
    explicit_month_year = re.search(
        r"\b("
        + "|".join(MONTH_NAMES.keys())
        + r")\s+(\d{4})\b",
        text_l,
    )
    if explicit_month_year:
        month_name = explicit_month_year.group(1)
        month_num  = MONTH_NAMES[month_name]
        year       = int(explicit_month_year.group(2))
        first = datetime.date(year, month_num, 1)
        last  = _last_day(year, month_num)
        return {"start_date": str(first), "end_date": str(last)}

    # 4b. Month RANGE: "April to May", "April through May", "from April to May",
    #     "between April and May"  → first day of first month … last day of second month
    month_range = re.search(
        r"(?:from\s+)?(?:between\s+)?(\b"
        + "|".join(MONTH_NAMES.keys())
        + r"\b)\s*(?:to|through|thru|till|until|and|-)\s*(\b"
        + "|".join(MONTH_NAMES.keys())
        + r"\b)",
        text_l,
    )
    if month_range:
        m1_name = month_range.group(1)
        m2_name = month_range.group(2)
        m1_num = MONTH_NAMES[m1_name]
        m2_num = MONTH_NAMES[m2_name]
        # If end month is before start month, assume they span a year boundary
        if m2_num < m1_num:
            end_year = ds_year + 1
        else:
            end_year = ds_year
        first = datetime.date(ds_year, m1_num, 1)
        last = _last_day(end_year, m2_num)
        return {"start_date": str(first), "end_date": str(last)}

    # 5. Named month WITHOUT explicit year → use DATASET year
    implicit_month = re.search(
        r"\b(?:in|during|entire|complete|for\s+)?\s*("
        + "|".join(MONTH_NAMES.keys())
        + r")\b",
        text_l,
    )
    if implicit_month:
        month_name = implicit_month.group(1)
        month_num  = MONTH_NAMES[month_name]
        first = datetime.date(ds_year, month_num, 1)
        last  = _last_day(ds_year, month_num)
        return {"start_date": str(first), "end_date": str(last)}

    # 6. Explicit date formats
    dates = _extract_explicit_dates(text)
    if len(dates) == 2:
        return {"start_date": dates[0], "end_date": dates[1]}
    if len(dates) == 1:
        return {"start_date": dates[0], "end_date": dates[0]}

    return None


def validate_date_range(start_date: str, end_date: str, db_min: str, db_max: str) -> str | None:
    """
    Validate date range in spec-defined order:
      5. Date format
      6. Database date range
      7. Logical date order

    Returns an error message string, or None if all valid.
    """
    # 5. Format validation
    try:
        start = datetime.date.fromisoformat(start_date)
        end   = datetime.date.fromisoformat(end_date)
    except (ValueError, TypeError):
        return "The provided date format is invalid. Please use DD/MM/YYYY or YYYY-MM-DD."

    db_start = datetime.date.fromisoformat(db_min)
    db_end   = datetime.date.fromisoformat(db_max)

    # 6. Database range
    if end < db_start or start > db_end:
        return (
            f"The requested date range is outside the available database period "
            f"({db_min} to {db_max})."
        )

    # 7. Logical order
    if start > end:
        return (
            f"The provided date range is invalid: start date ({start_date}) "
            f"is after end date ({end_date}). Please enter a valid date range."
        )

    return None  # valid