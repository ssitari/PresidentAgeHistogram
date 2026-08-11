#!/usr/bin/env python3
"""
Build president-age tables for distribution charts.

Outputs:
  presidents.csv            - reference table, one row per presidency (47)
  presidents_july4.csv      - one row per July 4, 1789-2026 (238)
  president_age_days.csv    - presidency x integer age x days served (no sampling, nobody dropped)
  president_age_totals.csv  - integer age x total days, all presidencies collapsed

Re-sample on any date by changing SAMPLE_MONTH / SAMPLE_DAY.
"""

import csv
from datetime import date, timedelta

AS_OF = date(2026, 8, 11)      # today; caps the incumbent's tenure
SAMPLE_MONTH, SAMPLE_DAY = 7, 4
SAMPLE_START_YEAR, SAMPLE_END_YEAR = 1789, 2026

# ---------------------------------------------------------------------------
# person_id, name, birth, death (None = living)
# ---------------------------------------------------------------------------
PEOPLE = {
    "washington":  ("George Washington",      date(1732, 2, 22), date(1799, 12, 14)),
    "jadams":      ("John Adams",             date(1735, 10, 30), date(1826, 7, 4)),
    "jefferson":   ("Thomas Jefferson",       date(1743, 4, 13), date(1826, 7, 4)),
    "madison":     ("James Madison",          date(1751, 3, 16), date(1836, 6, 28)),
    "monroe":      ("James Monroe",           date(1758, 4, 28), date(1831, 7, 4)),
    "jqadams":     ("John Quincy Adams",      date(1767, 7, 11), date(1848, 2, 23)),
    "jackson":     ("Andrew Jackson",         date(1767, 3, 15), date(1845, 6, 8)),
    "vanburen":    ("Martin Van Buren",       date(1782, 12, 5), date(1862, 7, 24)),
    "whharrison":  ("William Henry Harrison", date(1773, 2, 9),  date(1841, 4, 4)),
    "tyler":       ("John Tyler",             date(1790, 3, 29), date(1862, 1, 18)),
    "polk":        ("James K. Polk",          date(1795, 11, 2), date(1849, 6, 15)),
    "taylor":      ("Zachary Taylor",         date(1784, 11, 24), date(1850, 7, 9)),
    "fillmore":    ("Millard Fillmore",       date(1800, 1, 7),  date(1874, 3, 8)),
    "pierce":      ("Franklin Pierce",        date(1804, 11, 23), date(1869, 10, 8)),
    "buchanan":    ("James Buchanan",         date(1791, 4, 23), date(1868, 6, 1)),
    "lincoln":     ("Abraham Lincoln",        date(1809, 2, 12), date(1865, 4, 15)),
    "ajohnson":    ("Andrew Johnson",         date(1808, 12, 29), date(1875, 7, 31)),
    "grant":       ("Ulysses S. Grant",       date(1822, 4, 27), date(1885, 7, 23)),
    "hayes":       ("Rutherford B. Hayes",    date(1822, 10, 4), date(1893, 1, 17)),
    "garfield":    ("James A. Garfield",      date(1831, 11, 19), date(1881, 9, 19)),
    "arthur":      ("Chester A. Arthur",      date(1829, 10, 5), date(1886, 11, 18)),
    "cleveland":   ("Grover Cleveland",       date(1837, 3, 18), date(1908, 6, 24)),
    "bharrison":   ("Benjamin Harrison",      date(1833, 8, 20), date(1901, 3, 13)),
    "mckinley":    ("William McKinley",       date(1843, 1, 29), date(1901, 9, 14)),
    "troosevelt":  ("Theodore Roosevelt",     date(1858, 10, 27), date(1919, 1, 6)),
    "taft":        ("William Howard Taft",    date(1857, 9, 15), date(1930, 3, 8)),
    "wilson":      ("Woodrow Wilson",         date(1856, 12, 28), date(1924, 2, 3)),
    "harding":     ("Warren G. Harding",      date(1865, 11, 2), date(1923, 8, 2)),
    "coolidge":    ("Calvin Coolidge",        date(1872, 7, 4),  date(1933, 1, 5)),
    "hoover":      ("Herbert Hoover",         date(1874, 8, 10), date(1964, 10, 20)),
    "fdr":         ("Franklin D. Roosevelt",  date(1882, 1, 30), date(1945, 4, 12)),
    "truman":      ("Harry S. Truman",        date(1884, 5, 8),  date(1972, 12, 26)),
    "eisenhower":  ("Dwight D. Eisenhower",   date(1890, 10, 14), date(1969, 3, 28)),
    "kennedy":     ("John F. Kennedy",        date(1917, 5, 29), date(1963, 11, 22)),
    "lbj":         ("Lyndon B. Johnson",      date(1908, 8, 27), date(1973, 1, 22)),
    "nixon":       ("Richard Nixon",          date(1913, 1, 9),  date(1994, 4, 22)),
    "ford":        ("Gerald Ford",            date(1913, 7, 14), date(2006, 12, 26)),
    "carter":      ("Jimmy Carter",           date(1924, 10, 1), date(2024, 12, 29)),
    "reagan":      ("Ronald Reagan",          date(1911, 2, 6),  date(2004, 6, 5)),
    "ghwbush":     ("George H. W. Bush",      date(1924, 6, 12), date(2018, 11, 30)),
    "clinton":     ("Bill Clinton",           date(1946, 8, 19), None),
    "gwbush":      ("George W. Bush",         date(1946, 7, 6),  None),
    "obama":       ("Barack Obama",           date(1961, 8, 4),  None),
    "trump":       ("Donald Trump",           date(1946, 6, 14), None),
    "biden":       ("Joe Biden",              date(1942, 11, 20), None),
}

# ---------------------------------------------------------------------------
# presidency_number, person_id, start, end (None = incumbent), party, note
# Start/end are the constitutional term boundaries. Where a Sunday pushed the
# public ceremony a day later (Monroe 1821, Taylor 1849, Hayes 1877, Wilson
# 1917, Eisenhower 1957, Reagan 1985, Obama 2013) the legal term is used.
# ---------------------------------------------------------------------------
PRESIDENCIES = [
    (1,  "washington", date(1789, 4, 30), date(1797, 3, 4),  "Unaffiliated",
     "Office vacant Mar 4 - Apr 30, 1789; government began before the president did"),
    (2,  "jadams",     date(1797, 3, 4),  date(1801, 3, 4),  "Federalist", ""),
    (3,  "jefferson",  date(1801, 3, 4),  date(1809, 3, 4),  "Democratic-Republican", ""),
    (4,  "madison",    date(1809, 3, 4),  date(1817, 3, 4),  "Democratic-Republican", ""),
    (5,  "monroe",     date(1817, 3, 4),  date(1825, 3, 4),  "Democratic-Republican", ""),
    (6,  "jqadams",    date(1825, 3, 4),  date(1829, 3, 4),  "National Republican", ""),
    (7,  "jackson",    date(1829, 3, 4),  date(1837, 3, 4),  "Democratic", ""),
    (8,  "vanburen",   date(1837, 3, 4),  date(1841, 3, 4),  "Democratic", ""),
    (9,  "whharrison", date(1841, 3, 4),  date(1841, 4, 4),  "Whig",
     "Died in office after 31 days; never held office on a July 4"),
    (10, "tyler",      date(1841, 4, 4),  date(1845, 3, 4),  "Whig",
     "Expelled from the Whig Party Sept 1841; unaffiliated thereafter"),
    (11, "polk",       date(1845, 3, 4),  date(1849, 3, 4),  "Democratic", ""),
    (12, "taylor",     date(1849, 3, 5),  date(1850, 7, 9),  "Whig",
     "Sworn Mar 5 (Mar 4 was a Sunday); died July 9, 1850, five days after his only July 4 in office"),
    (13, "fillmore",   date(1850, 7, 9),  date(1853, 3, 4),  "Whig", ""),
    (14, "pierce",     date(1853, 3, 4),  date(1857, 3, 4),  "Democratic", ""),
    (15, "buchanan",   date(1857, 3, 4),  date(1861, 3, 4),  "Democratic", ""),
    (16, "lincoln",    date(1861, 3, 4),  date(1865, 4, 15), "Republican",
     "Assassinated in office"),
    (17, "ajohnson",   date(1865, 4, 15), date(1869, 3, 4),  "National Union",
     "Elected as a Democrat on the National Union ticket"),
    (18, "grant",      date(1869, 3, 4),  date(1877, 3, 4),  "Republican", ""),
    (19, "hayes",      date(1877, 3, 4),  date(1881, 3, 4),  "Republican",
     "Took the oath privately Mar 3, 1877; public ceremony Mar 5"),
    (20, "garfield",   date(1881, 3, 4),  date(1881, 9, 19), "Republican",
     "Shot July 2, 1881; in office but incapacitated on July 4; died Sept 19"),
    (21, "arthur",     date(1881, 9, 19), date(1885, 3, 4),  "Republican", ""),
    (22, "cleveland",  date(1885, 3, 4),  date(1889, 3, 4),  "Democratic",
     "First of two non-consecutive terms"),
    (23, "bharrison",  date(1889, 3, 4),  date(1893, 3, 4),  "Republican", ""),
    (24, "cleveland",  date(1893, 3, 4),  date(1897, 3, 4),  "Democratic",
     "Second of two non-consecutive terms"),
    (25, "mckinley",   date(1897, 3, 4),  date(1901, 9, 14), "Republican",
     "Assassinated in office"),
    (26, "troosevelt", date(1901, 9, 14), date(1909, 3, 4),  "Republican",
     "Took office at 42, youngest ever; had turned 43 by his first July 4 in office"),
    (27, "taft",       date(1909, 3, 4),  date(1913, 3, 4),  "Republican", ""),
    (28, "wilson",     date(1913, 3, 4),  date(1921, 3, 4),  "Democratic", ""),
    (29, "harding",    date(1921, 3, 4),  date(1923, 8, 2),  "Republican",
     "Died in office"),
    (30, "coolidge",   date(1923, 8, 2),  date(1929, 3, 4),  "Republican",
     "Born on July 4; the only president whose birthday coincides with the sample date"),
    (31, "hoover",     date(1929, 3, 4),  date(1933, 3, 4),  "Republican", ""),
    (32, "fdr",        date(1933, 3, 4),  date(1945, 4, 12), "Democratic",
     "Died in office; longest tenure, 12 July 4ths"),
    (33, "truman",     date(1945, 4, 12), date(1953, 1, 20), "Democratic", ""),
    (34, "eisenhower", date(1953, 1, 20), date(1961, 1, 20), "Republican", ""),
    (35, "kennedy",    date(1961, 1, 20), date(1963, 11, 22), "Democratic",
     "Assassinated in office"),
    (36, "lbj",        date(1963, 11, 22), date(1969, 1, 20), "Democratic", ""),
    (37, "nixon",      date(1969, 1, 20), date(1974, 8, 9),  "Republican",
     "Resigned"),
    (38, "ford",       date(1974, 8, 9),  date(1977, 1, 20), "Republican",
     "Never elected president or vice president"),
    (39, "carter",     date(1977, 1, 20), date(1981, 1, 20), "Democratic", ""),
    (40, "reagan",     date(1981, 1, 20), date(1989, 1, 20), "Republican", ""),
    (41, "ghwbush",    date(1989, 1, 20), date(1993, 1, 20), "Republican", ""),
    (42, "clinton",    date(1993, 1, 20), date(2001, 1, 20), "Democratic", ""),
    (43, "gwbush",     date(2001, 1, 20), date(2009, 1, 20), "Republican", ""),
    (44, "obama",      date(2009, 1, 20), date(2017, 1, 20), "Democratic", ""),
    (45, "trump",      date(2017, 1, 20), date(2021, 1, 20), "Republican",
     "First of two non-consecutive terms"),
    (46, "biden",      date(2021, 1, 20), date(2025, 1, 20), "Democratic", ""),
    (47, "trump",      date(2025, 1, 20), None,              "Republican",
     "Second of two non-consecutive terms; incumbent"),
]


def age_parts(birth, on):
    """Return (years, days_into_year) at a given date."""
    years = on.year - birth.year
    try:
        anniv = birth.replace(year=birth.year + years)
    except ValueError:                      # Feb 29 birthdays; none here
        anniv = birth.replace(year=birth.year + years, day=28)
    if anniv > on:
        years -= 1
        try:
            anniv = birth.replace(year=birth.year + years)
        except ValueError:
            anniv = birth.replace(year=birth.year + years, day=28)
    return years, (on - anniv).days


def age_exact(birth, on):
    return (on - birth).days / 365.2425


def term_end(p_end):
    return p_end if p_end is not None else AS_OF


def president_on(d):
    """Presidency in office on date d. Term boundaries: outgoing ends, incoming begins."""
    for num, pid, start, end, party, note in PRESIDENCIES:
        e = term_end(end)
        if start <= d < e or (end is None and d == AS_OF):
            return (num, pid, start, end, party, note)
        # transition day belongs to the incoming president; handled by start <= d
    return None


# ---------------------------------------------------------------------------
# 1. Reference table
# ---------------------------------------------------------------------------
ref_rows = []
for num, pid, start, end, party, note in PRESIDENCIES:
    name, birth, death = PEOPLE[pid]
    e = term_end(end)
    sy, sd = age_parts(birth, start)
    ey, ed = age_parts(birth, e)
    ref_rows.append({
        "presidency_number": num,
        "person_id": pid,
        "name": name,
        "party": party,
        "birth_date": birth.isoformat(),
        "death_date": death.isoformat() if death else "",
        "term_start": start.isoformat(),
        "term_end": end.isoformat() if end else "",
        "incumbent": "TRUE" if end is None else "FALSE",
        "days_in_office": (e - start).days,
        "age_at_start_years": sy,
        "age_at_start_days": sd,
        "age_at_start_exact": round(age_exact(birth, start), 4),
        "age_at_end_years": ey,
        "age_at_end_days": ed,
        "age_at_end_exact": round(age_exact(birth, e), 4),
        "note": note,
    })

with open("/home/claude/presidents.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ref_rows[0].keys()))
    w.writeheader()
    w.writerows(ref_rows)

# ---------------------------------------------------------------------------
# 2. Sampled series (July 4 by default)
# ---------------------------------------------------------------------------
sample_rows = []
for year in range(SAMPLE_START_YEAR, SAMPLE_END_YEAR + 1):
    d = date(year, SAMPLE_MONTH, SAMPLE_DAY)
    hit = president_on(d)
    if hit is None:
        continue
    num, pid, start, end, party, note = hit
    name, birth, death = PEOPLE[pid]
    y, dd = age_parts(birth, d)
    e = term_end(end)
    sample_rows.append({
        "sample_date": d.isoformat(),
        "year": year,
        "presidency_number": num,
        "person_id": pid,
        "name": name,
        "party": party,
        "age_years": y,
        "age_days": dd,
        "age_exact": round(age_exact(birth, d), 4),
        "days_into_term": (d - start).days,
        "days_remaining_in_term": (e - d).days,
        "term_start": start.isoformat(),
        "term_end": end.isoformat() if end else "",
    })

with open("/home/claude/presidents_july4.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(sample_rows[0].keys()))
    w.writeheader()
    w.writerows(sample_rows)

# ---------------------------------------------------------------------------
# 3. Day-weighted table: presidency x integer age x days served
#    No sampling, so every presidency appears, Harrison included.
# ---------------------------------------------------------------------------
age_days_rows = []
for num, pid, start, end, party, note in PRESIDENCIES:
    name, birth, death = PEOPLE[pid]
    e = term_end(end)
    counts = {}
    d = start
    while d < e:
        y, _ = age_parts(birth, d)
        counts[y] = counts.get(y, 0) + 1
        d += timedelta(days=1)
    for y in sorted(counts):
        age_days_rows.append({
            "presidency_number": num,
            "person_id": pid,
            "name": name,
            "party": party,
            "age_years": y,
            "days_at_this_age": counts[y],
        })

with open("/home/claude/president_age_days.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(age_days_rows[0].keys()))
    w.writeheader()
    w.writerows(age_days_rows)

totals = {}
for r in age_days_rows:
    totals[r["age_years"]] = totals.get(r["age_years"], 0) + r["days_at_this_age"]
with open("/home/claude/president_age_totals.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["age_years", "total_days", "total_years"])
    for y in sorted(totals):
        w.writerow([y, totals[y], round(totals[y] / 365.2425, 3)])

print(f"presidents.csv            {len(ref_rows)} rows")
print(f"presidents_july4.csv      {len(sample_rows)} rows")
print(f"president_age_days.csv    {len(age_days_rows)} rows")
print(f"president_age_totals.csv  {len(totals)} rows")
