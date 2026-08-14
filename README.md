# Presidential ages in office

An interactive unit histogram (Wilkinson dot plot) of how old presidents were
while they held the office, plus the four CSVs and the generator behind it.

---

## Live demo

[View on GitHub Pages](https://ssitari.github.io/PresidentAgeHistogram/)

---

## The chart

`index.html` + `app.js` + `config.js`. It uses ES modules and `fetch`, so it has
to be served over HTTP:

```bash
python3 -m http.server 8000   # or: npx serve .
```

Then open `http://localhost:8000`.

**One dot = one president at one integer age.** The source is
`president_age_days.csv`, which does no sampling, so every president appears —
including William Henry Harrison, whose entire presidency is a single dot at 68.
The grid is 41 age bins wide and 17 dots tall at the mode (ages 57 and 58).

Within a column, dots stack in chronological order: the earliest president to
reach that age sits on the axis. Reading a column bottom-to-top is reading
forward in time.

### Dots: whole vs. filled

The **whole units** mode treats every dot the same — a true unit histogram of
282 president-ages. The default **fill by days at age** mode draws each dot as a
clock face, with the wedge showing how much of that year was actually served.
92 of the 282 dots are partial, so the difference is not cosmetic: it is what
separates "was 68 at some point" from Harrison's 31 days. The dot count is
identical either way; only the ink changes.

### Selecting

The left column lists presidents in order, which makes it a time axis as much as
a legend. **Drag down it to brush an era** and the matching dots stay lit while
the rest drop back; **click a name** to toggle one on its own. Escape or *Clear
selection* resets. Hovering either panel rings the matching dots and shows terms,
dates, and days served — including the age runs, which is where Cleveland's and
Trump's split spans are legible.

### Combining non-consecutive terms

`COMBINE_NONCONSECUTIVE` in `config.js` is `true`, so Cleveland and Trump each
get one legend row rather than two. A person's place in the list is their *first*
presidency, which puts Trump at position 45, before Biden. Their age spans are
drawn as separate segments and printed as separate runs (`47–51, 55–59`) so the
gap years are never implied to be time in office. Set the flag to `false` for 47
rows, one per presidency.

### Color

Party by default, on a six-slot palette (the three single-presidency parties
fold into "Other historical party") checked for colorblind separation of
adjacent pairs against a white surface. Switch to *Uniform* to read the chart as
one distribution rather than six series. Selection is always signalled by
dimming the unselected, never by recoloring, so it cannot collide with a party
hue.

### Callouts

Two labels sit above the plot: the youngest and the oldest dot. Both are derived
from the data rather than written in, so they follow if the tables change.
`CALLOUTS` in `config.js` controls which appear — a third, `'briefest'`, marks
the fewest days served at any one age (Washington's 10 days at 65, not
Harrison's 31 at 68) and is off by default. An empty array removes them all.

The *Table* view carries the same 45 rows as plain text — the accessible path to
everything the tooltips say, and it responds to the same selection.

## The data

Four CSVs plus the generator that made them. Dates are ISO. Term boundaries are the
constitutional ones — where a Sunday pushed the public ceremony a day later (Monroe 1821,
Taylor 1849, Hayes 1877, Wilson 1917, Eisenhower 1957, Reagan 1985, Obama 2013) the legal
date is used, which matters for none of the July 4 sampling.

## presidents.csv — 47 rows

One row per *presidency*, not per person. Cleveland and Trump each appear twice, so
`person_id` groups them and `presidency_number` separates them. Includes birth and death
dates, party, days in office, and age at start and end in both `years`/`days` and decimal
form. The `note` column carries the edge cases in prose.

Ages are given three ways throughout: `age_years` (integer, for binning), `age_days`
(days past that birthday, for exact ordering within a bin), and `age_exact` (decimal
years, for beeswarms or anything continuous).

## presidents_july4.csv — 238 rows

The original sampled design, kept for reference; the chart does not use it. Whoever
held the office on July 4 of each year, 1789–2026. No gaps.
Also carries `days_into_term` and `days_remaining_in_term`, which lets you filter to
first-year vs. lame-duck observations later if you want.

What the sampling does:

- **William Henry Harrison is absent entirely** — 31 days in office, none of them a July 4.
  He is the *only* presidency the sample drops.
- **Theodore Roosevelt's 42 disappears.** He took office at 42 in September 1901 but had
  turned 43 by July 4, 1902. The floor of this series is 43, not the famous 42.
- **Garfield is present in 1881** at 49, having been shot on July 2 and lying incapacitated.
- **Taylor's only July 4 in office is 1850**, five days before he died of an illness
  contracted at that day's ceremony.
- **Coolidge was born on July 4**, so his five sampled ages are all exactly `Ny 0d`.
- FDR contributes 12 observations; Washington, Jefferson, and Madison 8 each.
- Range: 43 (TR, 1902) to 81 (Biden, 2024). Trump is 80 on July 4, 2026.

## president_age_days.csv — 282 rows

What the chart reads. One row per presidency × integer age, with `days_at_this_age`. No sampling at
all, so nobody is excluded on a technicality — Harrison shows up as 31 days at 68, Garfield
as 199 days at 49. Feed this to the same stacked histogram with bar height = days instead
of count and you get the identical chart shape with full coverage. Totals 86,664 days
(237.3 years), one day short of the full span because the incumbent's current day is
still open.

## president_age_totals.csv — 41 rows

`president_age_days.csv` collapsed across presidencies: integer age × total days × total
years. The unstacked envelope, for a reference outline or a small multiple.

Ages 42 and 82 exist here and nowhere in the July 4 sample: TR's 43 days at 42 in autumn
1901, and Biden's 61 days at 82 between November 2024 and January 2025.

## build_president_ages.py

Change `SAMPLE_MONTH` / `SAMPLE_DAY` at the top and re-run to resample on any date —
January 1, Inauguration Day, election day, whatever. `AS_OF` caps the incumbent's tenure
and should be bumped when you regenerate.

---

## Acknowledgements

Most of the code written with assistance from [Claude](https://claude.ai) (Anthropic).
