#!/usr/bin/env python3
"""
Build president-age tables for distribution charts.

Outputs (written next to this script):
  presidents.csv            - reference table, one row per presidency (47)
  presidents_july4.csv      - one row per July 4, 1789-2026
  president_age_days.csv    - presidency x integer age x days served (no sampling)
  president_age_totals.csv  - integer age x total days, all presidencies collapsed

Sources
-------
Terms, parties and birth dates:
    unitedstates/congress-legislators -> executive.json (public domain)
    https://unitedstates.github.io/congress-legislators/executive.json
    The same project the companion Senate chart uses.

Death dates:
    Wikidata (CC0), via SPARQL, joined on presidency ordinal (P1545).
    executive.json carries no death dates, and death_date is an output
    column only -- nothing here computes with it.

Nothing in this file is typed from memory. Everything except the editorial
NOTES below is fetched and can be re-derived by anyone; that is the point.
An earlier version hard-coded every birth, death and term date by hand,
which made the tables unverifiable and unreproducible even though the
values were, as it turned out, almost entirely correct.

Stdlib only. Downloads cache into data/; pass --refresh to re-download.
Re-sample on any date by changing SAMPLE_MONTH / SAMPLE_DAY.
"""

import csv
import json
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

AS_OF = date(2026, 8, 11)      # today; caps the incumbent's tenure
SAMPLE_MONTH, SAMPLE_DAY = 7, 4
SAMPLE_START_YEAR, SAMPLE_END_YEAR = 1789, 2026

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
EXECUTIVE_URL = "https://unitedstates.github.io/congress-legislators/executive.json"
EXECUTIVE_FILE = "executive.json"
DEATHS_FILE = "president_deaths.csv"

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_QUERY = """
SELECT ?ordinal ?pLabel ?death WHERE {
  ?p p:P39 ?st .
  ?st ps:P39 wd:Q11696 .
  ?st pq:P1545 ?ordinal .
  OPTIONAL { ?p wdt:P570 ?death }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

# congress-legislators spells parties its own way. config.js matches party
# strings exactly, so they are normalised to the labels the chart colours by;
# anything unmapped falls through to "Other historical party" there.
PARTY_LABELS = {
    "no party": "Unaffiliated",
    "Democrat": "Democratic",
}

# Conventional display forms, keyed by person_id. The source stores full
# formal names ("Jimmy Earl Carter", "Bill Jefferson Clinton"), which are
# correct but not how a chart label should read. These are presentation, not
# data -- the dates and terms below still come entirely from the source, and
# a name missing here simply falls back to the source's own form.
DISPLAY_NAMES = {
    "jkpolk": "James K. Polk",
    "usgrant": "Ulysses S. Grant",
    "rbhayes": "Rutherford B. Hayes",
    "jagarfield": "James A. Garfield",
    "caarthur": "Chester A. Arthur",
    "wgharding": "Warren G. Harding",
    "hchoover": "Herbert Hoover",
    "fdroosevelt": "Franklin D. Roosevelt",
    "ddeisenhower": "Dwight D. Eisenhower",
    "jfkennedy": "John F. Kennedy",
    "lbjohnson": "Lyndon B. Johnson",
    "rmnixon": "Richard Nixon",
    "grford": "Gerald Ford",
    "jecarter": "Jimmy Carter",
    "rwreagan": "Ronald Reagan",
    "ghbush": "George H. W. Bush",
    "wjclinton": "Bill Clinton",
    "gwbush": "George W. Bush",
    "bhobama": "Barack Obama",
    "djtrump": "Donald Trump",
    "jrbiden": "Joe Biden",
}

# ---------------------------------------------------------------------------
# Editorial notes, keyed by presidency number. These are prose, not data --
# the one thing here that is legitimately hand-written.
#
# On inauguration dates: where March 4 fell on a Sunday and the public
# ceremony was held a day later (Monroe 1821, Taylor 1849, Hayes 1877,
# Wilson 1917, Eisenhower 1957, Reagan 1985, Obama 2013), the source gives
# the legal term start and that is what these tables use. A previous
# hand-entered version stated that rule but broke it for Taylor alone,
# recording March 5.
# ---------------------------------------------------------------------------
NOTES = {
    1: "Office vacant Mar 4 - Apr 30, 1789; government began before the president did",
    9: "Died in office after 31 days; never held office on a July 4",
    10: "Expelled from the Whig Party Sept 1841; unaffiliated thereafter",
    12: "Legal term began Mar 4; sworn Mar 5 (Mar 4 was a Sunday). Died July 9, "
        "1850, five days after his only July 4 in office",
    16: "Assassinated in office",
    17: "Elected as a Democrat on the National Union ticket",
    19: "Took the oath privately Mar 3, 1877; public ceremony Mar 5",
    20: "Shot July 2, 1881; in office but incapacitated on July 4; died Sept 19",
    22: "First of two non-consecutive terms",
    24: "Second of two non-consecutive terms",
    25: "Assassinated in office",
    26: "Took office at 42, youngest ever; had turned 43 by his first July 4 in office",
    29: "Died in office",
    30: "Born on July 4; the only president whose birthday coincides with the sample date",
    32: "Died in office; longest tenure, 12 July 4ths",
    35: "Assassinated in office",
    37: "Resigned",
    38: "Never elected president or vice president",
    45: "First of two non-consecutive terms",
    47: "Second of two non-consecutive terms; incumbent",
}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
def fetch_executive(refresh=False):
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / EXECUTIVE_FILE
    if refresh or not path.exists():
        print(f"  downloading {EXECUTIVE_FILE} ...", flush=True)
        urllib.request.urlretrieve(EXECUTIVE_URL, path)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fetch_deaths(refresh=False):
    """{presidency ordinal: (label, death date or None)} from Wikidata."""
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / DEATHS_FILE
    if refresh or not path.exists():
        print("  querying Wikidata for death dates ...", flush=True)
        url = WIKIDATA_ENDPOINT + "?" + urllib.parse.urlencode({"query": WIKIDATA_QUERY})
        req = urllib.request.Request(url, headers={
            "Accept": "text/csv",
            # Wikidata asks for a descriptive agent on scripted queries.
            "User-Agent": "PresidentAgeHistogram/1.0 (github.com/ssitari/PresidentAgeHistogram)",
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)

    deaths = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            ordinal = (row.get("ordinal") or "").strip()
            # Wikidata holds non-integer ordinals for fictional presidents --
            # "8½" belongs to a Gravity Falls character. Integers only.
            if not ordinal.isdigit():
                continue
            death = (row.get("death") or "").strip()
            deaths[int(ordinal)] = (
                (row.get("pLabel") or "").strip(),
                date(*map(int, death[:10].split("-"))) if death else None,
            )
    return deaths


# ---------------------------------------------------------------------------
# Deriving presidencies
# ---------------------------------------------------------------------------
def ascii_fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def person_slug(name):
    """Initials + surname, e.g. 'jqadams'. Stable within a run; the app uses
    person_id only to group non-consecutive terms into one person."""
    initials = "".join(p[0] for p in name["parts"][:-1])
    return ascii_fold(initials + name["parts"][-1]).lower().replace(" ", "").replace("'", "")


def display_name(rec):
    """Nickname when the source carries one, so 'Jimmy Carter' not 'James'."""
    first = rec["name"].get("nickname") or rec["name"].get("first", "")
    middle = rec["name"].get("middle", "")
    last = rec["name"].get("last", "")
    parts = [p for p in (first, middle, last) if p]
    return " ".join(parts), {"parts": [p for p in ((rec["name"].get("first") or ""),
                                                   middle, last) if p]}


def build_presidencies(data):
    """Merge each president's contiguous terms into presidencies, ordered."""
    out = []
    for rec in data:
        terms = sorted([t for t in rec["terms"] if t.get("type") == "prez"],
                       key=lambda t: t["start"])
        if not terms:
            continue
        full, parts = display_name(rec)
        pid = person_slug(parts)
        full = DISPLAY_NAMES.get(pid, full)
        run = None
        for t in terms:
            if run and run["end"] == t["start"]:
                run["end"] = t["end"]          # contiguous: same presidency
            else:
                if run:
                    out.append(run)
                run = {"name": full, "parts": parts, "start": t["start"],
                       "end": t["end"], "party": t.get("party", "")}
        out.append(run)

    out.sort(key=lambda r: r["start"])
    iso = lambda s: date(*map(int, s.split("-")))
    presidencies = []
    for i, r in enumerate(out, start=1):
        start, end = iso(r["start"]), iso(r["end"])
        incumbent = end > AS_OF
        presidencies.append({
            "number": i,
            "person_id": person_slug(r["parts"]),
            "name": r["name"],
            "party": PARTY_LABELS.get(r["party"], r["party"]),
            "start": start,
            "end": None if incumbent else end,
            "note": NOTES.get(i, ""),
        })
    return presidencies


# ---------------------------------------------------------------------------
# Age maths
# ---------------------------------------------------------------------------
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


def main(refresh=False):
    print("Reading congress-legislators ...")
    data = fetch_executive(refresh)
    deaths = fetch_deaths(refresh)

    # birth dates, keyed the same way presidencies are
    births = {}
    for rec in data:
        if not any(t.get("type") == "prez" for t in rec["terms"]):
            continue
        _, parts = display_name(rec)
        bd = rec.get("bio", {}).get("birthday")
        if bd:
            births[person_slug(parts)] = date(*map(int, bd.split("-")))

    presidencies = build_presidencies(data)

    # --- validation: the ordinal join must line up with the source ---
    problems = []
    for p in presidencies:
        if p["person_id"] not in births:
            problems.append(f"no birth date for {p['name']} (#{p['number']})")
        label, _ = deaths.get(p["number"], ("", None))
        if label and ascii_fold(p["name"].split()[-1]).lower() not in ascii_fold(label).lower():
            problems.append(
                f"#{p['number']} ordinal join looks wrong: source '{p['name']}' vs Wikidata '{label}'")
    if problems:
        print("\n  VALIDATION PROBLEMS:")
        for m in problems:
            print("   ", m)
        sys.exit("Refusing to write tables from a questionable join.")
    print(f"  {len(presidencies)} presidencies, {len(births)} people, "
          f"{sum(1 for v in deaths.values() if v[1])} death dates")

    def person(p):
        return p["name"], births[p["person_id"]], deaths.get(p["number"], ("", None))[1]

    def president_on(d):
        for p in presidencies:
            if p["start"] <= d < term_end(p["end"]) or (p["end"] is None and d == AS_OF):
                return p
        return None

    # 1. Reference table -----------------------------------------------------
    ref_rows = []
    for p in presidencies:
        name, birth, death = person(p)
        e = term_end(p["end"])
        sy, sd = age_parts(birth, p["start"])
        ey, ed = age_parts(birth, e)
        ref_rows.append({
            "presidency_number": p["number"],
            "person_id": p["person_id"],
            "name": name,
            "party": p["party"],
            "birth_date": birth.isoformat(),
            "death_date": death.isoformat() if death else "",
            "term_start": p["start"].isoformat(),
            "term_end": p["end"].isoformat() if p["end"] else "",
            "incumbent": "TRUE" if p["end"] is None else "FALSE",
            "days_in_office": (e - p["start"]).days,
            "age_at_start_years": sy,
            "age_at_start_days": sd,
            "age_at_start_exact": round(age_exact(birth, p["start"]), 4),
            "age_at_end_years": ey,
            "age_at_end_days": ed,
            "age_at_end_exact": round(age_exact(birth, e), 4),
            "note": p["note"],
        })
    write(HERE / "presidents.csv", ref_rows)

    # 2. Sampled series (July 4 by default) ---------------------------------
    sample_rows = []
    for year in range(SAMPLE_START_YEAR, SAMPLE_END_YEAR + 1):
        d = date(year, SAMPLE_MONTH, SAMPLE_DAY)
        p = president_on(d)
        if p is None:
            continue
        name, birth, _ = person(p)
        y, dd = age_parts(birth, d)
        e = term_end(p["end"])
        sample_rows.append({
            "sample_date": d.isoformat(),
            "year": year,
            "presidency_number": p["number"],
            "person_id": p["person_id"],
            "name": name,
            "party": p["party"],
            "age_years": y,
            "age_days": dd,
            "age_exact": round(age_exact(birth, d), 4),
            "days_into_term": (d - p["start"]).days,
            "days_remaining_in_term": (e - d).days,
            "term_start": p["start"].isoformat(),
            "term_end": p["end"].isoformat() if p["end"] else "",
        })
    write(HERE / "presidents_july4.csv", sample_rows)

    # 3. Day-weighted table --------------------------------------------------
    age_days_rows = []
    for p in presidencies:
        name, birth, _ = person(p)
        e = term_end(p["end"])
        counts = {}
        d = p["start"]
        while d < e:
            y, _u = age_parts(birth, d)
            counts[y] = counts.get(y, 0) + 1
            d += timedelta(days=1)
        for y in sorted(counts):
            age_days_rows.append({
                "presidency_number": p["number"],
                "person_id": p["person_id"],
                "name": name,
                "party": p["party"],
                "age_years": y,
                "days_at_this_age": counts[y],
            })
    write(HERE / "president_age_days.csv", age_days_rows)

    # 4. Collapsed totals ----------------------------------------------------
    totals = {}
    for r in age_days_rows:
        totals[r["age_years"]] = totals.get(r["age_years"], 0) + r["days_at_this_age"]
    with open(HERE / "president_age_totals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["age_years", "total_days", "total_years"])
        for y in sorted(totals):
            w.writerow([y, totals[y], round(totals[y] / 365.2425, 3)])

    print(f"presidents.csv            {len(ref_rows)} rows")
    print(f"presidents_july4.csv      {len(sample_rows)} rows")
    print(f"president_age_days.csv    {len(age_days_rows)} rows")
    print(f"president_age_totals.csv  {len(totals)} rows")


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
