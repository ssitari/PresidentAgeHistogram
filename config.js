// ============================================================
//  config.js  —  Edit this file to use your own data
// ============================================================
//
//  QUICK START
//  1. Point DATA_FILE / PEOPLE_FILE at your CSVs
//  2. Update the FIELD names to match your column headers
//  3. Serve the folder over HTTP and open index.html
//
//  The chart is a unit histogram (Wilkinson dot plot): one dot per
//  person x integer age. Nothing is sampled, so every person who held
//  the office appears, including the very short tenures.
//
// ============================================================

// One row per presidency x integer age, with days spent at that age.
export const DATA_FILE = './president_age_days.csv';

// One row per presidency, carrying the biographical detail for tooltips.
export const PEOPLE_FILE = './presidents.csv';

// ============================================================
//  FIELDS
//  Column names in the two CSVs above.
// ============================================================

export const FIELDS = {
  // ── president_age_days.csv ──
  personId:   'person_id',        // groups non-consecutive terms into one person
  termNumber: 'presidency_number',
  name:       'name',
  party:      'party',
  age:        'age_years',        // integer age — the histogram bin
  days:       'days_at_this_age', // days spent at that age while in office

  // ── presidents.csv ──
  birth:     'birth_date',
  death:     'death_date',
  termStart: 'term_start',
  termEnd:   'term_end',
  incumbent: 'incumbent',
  note:      'note',
};

// Label for one observation, singular / plural.
export const UNIT_LABEL = ['president-year', 'president-years'];

// Days in a full year — a dot is "whole" when days_at_this_age reaches this.
export const FULL_YEAR = 365;

// ============================================================
//  GROUPING
// ============================================================

// true  — Cleveland and Trump each appear once, their two terms merged
// false — one legend entry per presidency (47 rows instead of 45)
export const COMBINE_NONCONSECUTIVE = true;

// ============================================================
//  DEFAULTS
// ============================================================

export const DEFAULT_COLOR_MODE = 'uniform'; // 'uniform' | 'party'
export const DEFAULT_DOT_MODE    = 'partial'; // 'whole' | 'partial'

// ============================================================
//  COLOR
//  The party hues are checked for colorblind separation of adjacent pairs
//  against this page's light surface. Re-check if you swap them.
// ============================================================

// Single-hue fill used when colorMode is 'uniform'.
export const BASE_COLOR = '#3d5a80';

// Dots outside the current selection.
export const DESELECTED_COLOR   = '#b9b7b2';
export const DEEMPHASIS_OPACITY = 0.35;

// Ring drawn around dots belonging to the hovered president.
export const HOVER_COLOR = '#1a1a1a';

// Party fills. `match` lists the exact strings from the party column that
// fold into this entry; anything unmatched falls through to the last entry.
export const PARTY_COLORS = [
  { id: 'federalist',  label: 'Federalist',             color: '#6a51a3', match: ['Federalist'] },
  { id: 'demrep',      label: 'Democratic-Republican',  color: '#41ab5d', match: ['Democratic-Republican'] },
  { id: 'whig',        label: 'Whig',                   color: '#a63603', match: ['Whig'] },
  { id: 'democratic',  label: 'Democratic',             color: '#3182bd', match: ['Democratic'] },
  { id: 'republican',  label: 'Republican',             color: '#cb181d', match: ['Republican'] },
  { id: 'other',       label: 'Other historical party', color: '#009e9e', match: [] },
];

// ============================================================
//  LAYOUT
// ============================================================

export const DOT_GAP     = 3;   // surface gap between neighbouring dots, px
export const DOT_MIN     = 5;   // dots never render smaller than this diameter
export const DOT_MAX     = 26;  // ...nor larger
export const ROW_MIN     = 13;  // legend row height bounds, px
export const ROW_MAX     = 22;
