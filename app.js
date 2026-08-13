// ============================================================
//  app.js  —  Visualization engine
//  Do not edit unless you are modifying the tool itself.
// ============================================================

import {
  DATA_FILE, PEOPLE_FILE, FIELDS, UNIT_LABEL, FULL_YEAR,
  COMBINE_NONCONSECUTIVE,
  DEFAULT_COLOR_MODE, DEFAULT_DOT_MODE,
  BASE_COLOR, DESELECTED_COLOR, DEEMPHASIS_OPACITY, HOVER_COLOR, HOVER_RING_WIDTH,
  PARTY_COLORS,
  DOT_GAP, DOT_MIN, DOT_MAX, ROW_MIN, ROW_MAX, CALLOUTS,
} from './config.js';

const TAU = Math.PI * 2;

// ============================================================
//  STATE
// ============================================================

const state = {
  colorMode: DEFAULT_COLOR_MODE,
  dotMode:   DEFAULT_DOT_MODE,
  view:      'chart',
  selected:  new Set(),   // person keys; empty means "no filter", all shown lit
  hovered:   null,        // person key under the cursor, in either panel
};

let people = [];          // one entry per person (or per presidency, per config)
let peopleByKey = new Map();
let dots = [];            // one entry per person x integer age
let ages = [];            // contiguous integer age domain
let maxStack = 0;
let totalDays = 0;

// ============================================================
//  DOM
// ============================================================

const el = {
  chart:     document.getElementById('chart'),
  chartSvg:  d3.select('#chart-svg'),
  legendBox: document.getElementById('legend-scroll'),
  legendSvg: d3.select('#legend-svg'),
  tableWrap: document.getElementById('table-wrap'),
  table:     d3.select('#table'),
  tooltip:   document.getElementById('tooltip'),
  loading:   document.getElementById('loading'),
  readout:   document.getElementById('readout'),
  clearBtn:  document.getElementById('clear'),
  partyKey:  document.getElementById('party-key'),
};

let legendBrush = null;
let suppressBrushEnd = false;

// ============================================================
//  DATA SHAPING
// ============================================================

const partyEntry = party => PARTY_COLORS.find(p => p.match.includes(party))
                         ?? PARTY_COLORS[PARTY_COLORS.length - 1];

// Collapse a list of integer ages into contiguous [from, to] runs.
function ageRuns(list) {
  const out = [];
  for (const a of [...new Set(list)].sort(d3.ascending)) {
    const last = out[out.length - 1];
    if (last && a === last[1] + 1) last[1] = a;
    else out.push([a, a]);
  }
  return out;
}

const fmtRuns = runs => runs.map(([a, b]) => a === b ? `${a}` : `${a}–${b}`).join(', ');

function shape(ageRows, personRows) {
  // ── Group the biographical table by person ──
  const bioByPerson = d3.group(personRows, d => d[FIELDS.personId]);

  // ── A "key" is what the legend lists: a person, or a single presidency ──
  const keyOf = row => COMBINE_NONCONSECUTIVE
    ? row[FIELDS.personId]
    : `${row[FIELDS.personId]}#${row[FIELDS.termNumber]}`;

  // ── Collapse age rows to one dot per key x integer age ──
  const byKeyAge = new Map();
  for (const row of ageRows) {
    const key = keyOf(row);
    const age = +row[FIELDS.age];
    const id  = `${key}|${age}`;
    const rec = byKeyAge.get(id);
    if (rec) rec.days += +row[FIELDS.days];
    else byKeyAge.set(id, {
      key, age,
      days: +row[FIELDS.days],
      personId: row[FIELDS.personId],
      name: row[FIELDS.name],
      party: row[FIELDS.party],
      order: +row[FIELDS.termNumber],
    });
  }

  dots = [...byKeyAge.values()];

  // ── Build the person list, ordered by first presidency ──
  const byKey = d3.group(dots, d => d.key);
  people = [...byKey].map(([key, ds]) => {
    const first = d3.least(ds, d => d.order);
    const bios  = (bioByPerson.get(first.personId) ?? [])
      .filter(b => COMBINE_NONCONSECUTIVE || +b[FIELDS.termNumber] === first.order)
      .sort((a, b) => +a[FIELDS.termNumber] - +b[FIELDS.termNumber]);

    return {
      key,
      name:      first.name,
      party:     first.party,
      partyKey:  partyEntry(first.party).id,
      order:     d3.min(ds, d => d.order),
      numbers:   [...new Set(ds.map(d => d.order))].sort(d3.ascending),
      minAge:    d3.min(ds, d => d.age),
      maxAge:    d3.max(ds, d => d.age),
      // Non-consecutive terms leave a gap in the ages held; keep the runs
      // separate so nothing implies office was held in between.
      runs:      ageRuns(ds.map(d => d.age)),
      count:     ds.length,
      days:      d3.sum(ds, d => d.days),
      incumbent: bios.some(b => String(b[FIELDS.incumbent]).toUpperCase() === 'TRUE'),
      terms:     bios.map(b => ({
        start: b[FIELDS.termStart],
        end:   b[FIELDS.termEnd],
        note:  b[FIELDS.note],
      })),
      birth: bios[0]?.[FIELDS.birth] ?? '',
      death: bios[0]?.[FIELDS.death] ?? '',
      notes: bios.map(b => b[FIELDS.note]).filter(Boolean),
    };
  }).sort((a, b) => a.order - b.order);

  people.forEach((p, i) => { p.row = i; });
  peopleByKey = new Map(people.map(p => [p.key, p]));

  // ── Stack: within an age column, earliest president sits on the axis ──
  ages = d3.range(d3.min(dots, d => d.age), d3.max(dots, d => d.age) + 1);
  for (const [, column] of d3.group(dots, d => d.age)) {
    column.sort((a, b) => a.order - b.order)
          .forEach((d, i) => { d.stack = i; });
  }

  dots.forEach(d => {
    d.person   = peopleByKey.get(d.key);
    d.fraction = Math.min(1, d.days / FULL_YEAR);
  });

  maxStack  = d3.max(dots, d => d.stack) + 1;
  totalDays = d3.sum(dots, d => d.days);
}

// ============================================================
//  COLOR
// ============================================================

const partyColor = key => (PARTY_COLORS.find(p => p.id === key) ?? PARTY_COLORS[0]).color;

const isLit = key => state.selected.size === 0 || state.selected.has(key);

function fillFor(person) {
  if (!isLit(person.key)) return DESELECTED_COLOR;
  return state.colorMode === 'party' ? partyColor(person.partyKey) : BASE_COLOR;
}

const opacityFor = person => isLit(person.key) ? 1 : DEEMPHASIS_OPACITY;

// ============================================================
//  CHART
// ============================================================

const MARGIN = { top: 22, right: 20, bottom: 52, left: 44 };

function renderChart() {
  const width  = el.chart.clientWidth;
  const height = el.chart.clientHeight;
  if (!width || !height || state.view !== 'chart') return;

  const innerW = width  - MARGIN.left - MARGIN.right;
  const innerH = height - MARGIN.top  - MARGIN.bottom;
  if (innerW <= 0 || innerH <= 0) return;

  // One square cell per dot; the tighter of the two axes wins so that
  // columns stay close-packed in both directions.
  let step = Math.min(innerW / ages.length, innerH / maxStack);
  let size = Math.min(Math.max(step - DOT_GAP, DOT_MIN), DOT_MAX);
  step = size + DOT_GAP;

  const r     = size / 2;
  const plotW = ages.length * step;
  const plotH = maxStack * step;
  const left  = MARGIN.left + Math.max(0, (innerW - plotW) / 2);

  // The column count usually caps the dot size, leaving vertical slack. Spend
  // a little more of it above the peak than below the axis rather than pinning
  // the plot to the floor of the panel.
  const slack    = Math.max(0, innerH - plotH);
  const baseline = MARGIN.top + plotH + slack * 0.62;
  const plotTop  = baseline - plotH;

  const x = age => left + (age - ages[0] + 0.5) * step;
  const y = i   => baseline - (i + 0.5) * step;

  const svg = el.chartSvg.attr('width', width).attr('height', height);
  svg.selectAll('*').remove();

  // ── Count rules, behind the dots ──
  const countTicks = d3.range(5, maxStack + 1, 5);
  const gCount = svg.append('g');
  gCount.selectAll('line').data(countTicks).join('line')
    .attr('class', 'count-rule')
    .attr('x1', left).attr('x2', left + plotW)
    .attr('y1', d => Math.round(baseline - d * step) + 0.5)
    .attr('y2', d => Math.round(baseline - d * step) + 0.5);
  gCount.selectAll('text').data(countTicks).join('text')
    .attr('class', 'count-label')
    .attr('x', left - 8)
    .attr('y', d => baseline - d * step)
    .text(d => d);

  // ── Age axis ──
  const gAxis = svg.append('g');
  gAxis.append('line')
    .attr('class', 'axis-line')
    .attr('x1', left).attr('x2', left + plotW)
    .attr('y1', Math.round(baseline) + 0.5)
    .attr('y2', Math.round(baseline) + 0.5);

  gAxis.selectAll('.tick-mark').data(ages).join('line')
    .attr('class', 'tick-mark')
    .attr('x1', d => Math.round(x(d)) + 0.5)
    .attr('x2', d => Math.round(x(d)) + 0.5)
    .attr('y1', baseline)
    .attr('y2', d => baseline + (d % 5 === 0 ? 6 : 3));

  const labelStride = step < 16 ? 5 : step < 24 ? 2 : 1;
  gAxis.selectAll('.tick-label')
    .data(ages.filter(a => a % labelStride === 0 || a === ages[0] || a === ages[ages.length - 1]))
    .join('text')
    .attr('class', 'tick-label')
    .attr('x', d => x(d))
    .attr('y', baseline + 19)
    .text(d => d);

  gAxis.append('text')
    .attr('class', 'axis-title')
    .attr('x', left + plotW / 2)
    .attr('y', baseline + 40)
    .attr('text-anchor', 'middle')
    .text('Age in years while in office');

  svg.append('text')
    .attr('class', 'axis-title')
    .attr('transform', `translate(14,${baseline - plotH / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle')
    .text(`Presidents at this age`);

  // ── Dots ──
  const arc = d3.arc().innerRadius(0).outerRadius(r).startAngle(0);

  const g = svg.append('g').attr('class', 'dots');
  const dot = g.selectAll('g.dot').data(dots, d => `${d.key}|${d.age}`).join('g')
    .attr('class', 'dot')
    .attr('transform', d => `translate(${x(d.age)},${y(d.stack)})`);

  dot.append('path').attr('class', 'dot-fill');
  dot.append('circle').attr('class', 'dot-ring').attr('r', r);
  dot.append('circle')
    .attr('class', 'dot-hit')
    .attr('r', Math.max(r, 9))
    .on('mousemove', (event, d) => { setHover(d.key); showDotTip(event, d); })
    .on('mouseleave', () => { setHover(null); hideTip(); })
    .on('click', (event, d) => toggle(d.key));

  // Geometry that depends only on layout is set once; paint() handles the rest.
  chartPaint = () => {
    dot.select('.dot-fill')
      .attr('d', d => arc({ endAngle: TAU * (state.dotMode === 'whole' ? 1 : d.fraction) }))
      .attr('fill', d => fillFor(d.person))
      .attr('opacity', d => opacityFor(d.person));

    dot.select('.dot-ring')
      .attr('stroke', d => state.hovered === d.key ? HOVER_COLOR : fillFor(d.person))
      .attr('stroke-width', d => state.hovered === d.key ? HOVER_RING_WIDTH : 1)
      .attr('opacity', d => state.hovered === d.key ? 1
        : (state.dotMode === 'whole' ? 0 : opacityFor(d.person) * 0.75));
  };
  chartPaint();

  // ── Extremes, labelled above their (always short) columns ──
  const colHeight = d3.rollup(dots, v => v.length, d => d.age);
  const CALLOUT_DEFS = {
    youngest: { pick: ds => d3.least(ds, d => d.age),
                text: d => `Youngest: ${d.person.name} at ${d.age}` },
    oldest:   { pick: ds => d3.greatest(ds, d => d.age),
                text: d => `Oldest: ${d.person.name} at ${d.age}` },
    briefest: { pick: ds => d3.least(ds, d => d.days),
                text: d => `Briefest: ${d.person.name}, ${fmtInt(d.days)} days at ${d.age}` },
  };
  const callouts = CALLOUTS
    .map(k => CALLOUT_DEFS[k]).filter(Boolean)
    .map(def => ({ d: def.pick(dots), text: def.text }))
    .filter((c, i, all) => c.d && all.findIndex(o => o.d === c.d) === i);

  const gAnnot = svg.append('g').attr('class', 'annots');
  const placed = [];
  for (const c of callouts) {
    const label  = c.text(c.d);
    const cx     = x(c.d.age);
    const top    = baseline - colHeight.get(c.d.age) * step;
    const anchor = cx < left + plotW * 0.2 ? 'start'
                 : cx > left + plotW * 0.8 ? 'end' : 'middle';

    // Clear the whole silhouette the text will pass over, not just its own column.
    const w  = label.length * 5.4;
    const x0 = anchor === 'start' ? cx : anchor === 'end' ? cx - w : cx - w / 2;
    const x1 = x0 + w;
    const spanned = ages.filter(a => x(a) >= x0 - step && x(a) <= x1 + step);
    const clearOf = d3.max(spanned, a => colHeight.get(a) ?? 0) ?? 0;

    let ty = baseline - clearOf * step - 14;
    while (placed.some(p => Math.abs(p.ty - ty) < 13 && p.x1 > x0 && p.x0 < x1)) ty -= 15;
    ty = Math.max(MARGIN.top + 12, ty);
    if (top - ty < 10) continue;                      // no headroom; skip quietly
    placed.push({ ty, x0, x1 });

    gAnnot.append('line')
      .attr('class', 'annot-line')
      .attr('x1', cx).attr('x2', cx)
      .attr('y1', top - 3).attr('y2', ty + 4);
    gAnnot.append('text')
      .attr('class', 'annot')
      .attr('x', cx).attr('y', ty)
      .attr('text-anchor', anchor)
      .text(label);
  }

  // ── Footnote ──
  svg.append('text')
    .attr('class', 'annot')
    .attr('x', left)
    .attr('y', MARGIN.top - 8)
    .text(state.dotMode === 'whole'
      ? `One dot = one president at one integer age. ${dots.length} dots, nothing sampled.`
      : `One dot = one president at one integer age; the wedge is the share of that year actually served.`);
}

let chartPaint = () => {};

// ============================================================
//  LEGEND SIDEBAR
// ============================================================

let legendPaint = () => {};
let rowHeight = ROW_MIN;

function renderLegend() {
  const width = el.legendBox.clientWidth;
  if (!width) return;

  const avail = el.legendBox.clientHeight - 8;
  rowHeight = Math.min(Math.max(avail / people.length, ROW_MIN), ROW_MAX);
  const height = rowHeight * people.length + 6;

  const svg = el.legendSvg.attr('width', width).attr('height', height);
  svg.selectAll('*').remove();

  const g = svg.append('g').attr('transform', 'translate(0,3)');

  const row = g.selectAll('g.row').data(people, d => d.key).join('g')
    .attr('class', 'row')
    .attr('transform', d => `translate(0,${d.row * rowHeight})`);

  row.append('rect')
    .attr('class', 'row-band')
    .attr('x', 0).attr('y', 0)
    .attr('width', width).attr('height', rowHeight);

  row.append('circle')
    .attr('class', 'row-swatch')
    .attr('cx', 12).attr('cy', rowHeight / 2)
    .attr('r', 3.5);

  row.append('text')
    .attr('class', 'row-name')
    .attr('x', 23).attr('y', rowHeight / 2)
    .text(d => d.name);

  // ── Brush over the whole list; a click with no drag toggles one name ──
  legendBrush = d3.brushY()
    .extent([[0, 0], [width, height]])
    .on('brush end', onBrush);

  svg.append('g').attr('class', 'legend-brush').call(legendBrush);

  svg.on('mousemove', event => {
    const p = rowAt(d3.pointer(event, svg.node())[1]);
    setHover(p ? p.key : null);
    if (p) showPersonTip(event, p); else hideTip();
  }).on('mouseleave', () => { setHover(null); hideTip(); });

  legendPaint = () => {
    row.select('.row-band')
      .classed('is-sel', d => state.selected.has(d.key))
      .classed('is-hov', d => state.hovered === d.key);
    row.select('.row-swatch')
      .attr('fill', d => fillFor(d))
      .attr('opacity', d => opacityFor(d));
    row.select('.row-name')
      .classed('is-out', d => !isLit(d.key))
      .classed('is-sel', d => state.selected.has(d.key));
  };
  legendPaint();
}

function rowAt(py) {
  const i = Math.floor((py - 3) / rowHeight);
  return people[i] ?? null;
}

function onBrush(event) {
  if (suppressBrushEnd) return;

  // A click that never moved: brush reports an empty selection.
  if (!event.selection) {
    if (event.type === 'end' && event.sourceEvent) {
      const p = rowAt(d3.pointer(event.sourceEvent, el.legendSvg.node())[1]);
      if (p) { toggle(p.key); return; }
    }
    if (event.type === 'end') { state.selected.clear(); paint(); }
    return;
  }

  const [y0, y1] = event.selection;
  state.selected = new Set(
    people.filter(p => {
      const c = 3 + (p.row + 0.5) * rowHeight;
      return c >= y0 && c <= y1;
    }).map(p => p.key)
  );
  paint();
}

function toggle(key) {
  clearBrushRect();
  if (state.selected.has(key)) state.selected.delete(key);
  else state.selected.add(key);
  paint();
}

function clearBrushRect() {
  if (!legendBrush) return;
  suppressBrushEnd = true;
  el.legendSvg.select('.legend-brush').call(legendBrush.move, null);
  suppressBrushEnd = false;
}

function setHover(key) {
  if (state.hovered === key) return;
  state.hovered = key;
  chartPaint();
  legendPaint();
  highlightTableRow();
}

// ============================================================
//  TABLE VIEW
// ============================================================

const fmtInt = d3.format(',');
const fmtDate = iso => {
  if (!iso) return '—';
  const d = new Date(iso + 'T00:00:00');
  return d3.utcFormat('%b %-d, %Y')(d);
};

function renderTable() {
  const cols = [
    { key: 'name',  label: 'President', cell: p =>
      `<span class="swatch" style="background:${state.colorMode === 'party' ? partyColor(p.partyKey) : BASE_COLOR}"></span>${p.name}` },
    { key: 'party', label: 'Party',     cell: p => p.party },
    { key: 'num',   label: 'Presidency', num: true, cell: p => p.numbers.join(', ') },
    { key: 'term',  label: 'Term(s)',   cell: p => p.terms
        .map(t => `${fmtDate(t.start)} – ${t.end ? fmtDate(t.end) : 'present'}`).join('<br>') },
    { key: 'range', label: 'Ages in office', num: true, cell: p => fmtRuns(p.runs) },
    { key: 'count', label: 'Dots', num: true, cell: p => p.count },
    { key: 'days',  label: 'Days in office', num: true, cell: p => fmtInt(p.days) },
  ];

  const t = el.table;
  t.selectAll('*').remove();

  t.append('thead').append('tr').selectAll('th').data(cols).join('th')
    .attr('class', d => d.num ? 'num' : null)
    .text(d => d.label);

  const tbody = t.append('tbody');
  tbody.selectAll('tr').data(people, d => d.key).join('tr')
    .attr('data-key', d => d.key)
    .on('mouseenter', (e, d) => setHover(d.key))
    .on('mouseleave', () => setHover(null))
    .on('click', (e, d) => toggle(d.key))
    .selectAll('td').data(p => cols.map(c => ({ c, p }))).join('td')
      .attr('class', d => d.c.num ? 'num' : null)
      .html(d => d.c.cell(d.p));

  highlightTableRow();
}

function highlightTableRow() {
  el.table.selectAll('tbody tr')
    .classed('is-sel', d => state.selected.has(d.key))
    .style('opacity', d => isLit(d.key) ? 1 : 0.45);
}

// ============================================================
//  TOOLTIP
// ============================================================

function tipHTML(person, dot) {
  const swatch = state.colorMode === 'party' ? partyColor(person.partyKey) : BASE_COLOR;
  const head = `
    <div class="tt-name"><span class="swatch" style="background:${swatch}"></span>${person.name}</div>
    <div class="tt-party">${person.party} · presidency ${person.numbers.join(' & ')}</div>`;

  const body = dot
    ? `<div class="tt-stat">Age <b>${dot.age}</b> — <b>${fmtInt(dot.days)}</b> of ${FULL_YEAR} days served${
        dot.days < FULL_YEAR && person.incumbent && dot.age === person.maxAge ? ' <i>(still counting)</i>' : ''}</div>`
    : `<div class="tt-stat">Ages <b>${fmtRuns(person.runs)}</b> · <b>${person.count}</b> ${
        person.count === 1 ? UNIT_LABEL[0] : UNIT_LABEL[1]} · <b>${fmtInt(person.days)}</b> days</div>`;

  const terms = person.terms
    .map(t => `${fmtDate(t.start)} – ${t.end ? fmtDate(t.end) : 'present'}`).join('<br>');

  const meta = `<div class="tt-meta">${terms}<br>b. ${fmtDate(person.birth)}${
    person.death ? ` · d. ${fmtDate(person.death)}` : ''}</div>`;

  const note = person.notes.length
    ? `<div class="tt-note">${person.notes.join('<br>')}</div>` : '';

  return head + body + meta + note;
}

function placeTip(event, html) {
  const tip = el.tooltip;
  tip.innerHTML = html;
  tip.style.display = 'block';
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = event.clientX + 14, y = event.clientY + 14;
  if (x + w > window.innerWidth  - 8) x = event.clientX - w - 14;
  if (y + h > window.innerHeight - 8) y = event.clientY - h - 14;
  tip.style.left = Math.max(8, x) + 'px';
  tip.style.top  = Math.max(8, y) + 'px';
}

const showDotTip    = (event, d) => placeTip(event, tipHTML(d.person, d));
const showPersonTip = (event, p) => placeTip(event, tipHTML(p, null));
const hideTip       = () => { el.tooltip.style.display = 'none'; };

// ============================================================
//  PAINT / READOUT
// ============================================================

function paint() {
  chartPaint();
  legendPaint();
  highlightTableRow();
  updateReadout();
  el.clearBtn.disabled = state.selected.size === 0;
}

function updateReadout() {
  const sel = state.selected;
  const shown = sel.size ? dots.filter(d => sel.has(d.key)) : dots;
  const days  = sel.size ? d3.sum(shown, d => d.days) : totalDays;
  const who   = sel.size ? `${sel.size} of ${people.length} selected` : `${people.length} presidents`;
  el.readout.textContent =
    `${who} · ${fmtInt(shown.length)} ${shown.length === 1 ? UNIT_LABEL[0] : UNIT_LABEL[1]} · ${fmtInt(days)} days`;
}

function renderPartyKey() {
  const show = state.colorMode === 'party';
  el.partyKey.style.display = show ? 'flex' : 'none';
  if (!show) return;

  const used = new Set(people.map(p => p.partyKey));
  d3.select(el.partyKey).selectAll('div.key-item')
    .data(PARTY_COLORS.filter(p => used.has(p.id)), d => d.id)
    .join(enter => {
      const item = enter.append('div').attr('class', 'key-item');
      item.append('span').attr('class', 'swatch');
      item.append('span').attr('class', 'key-text');
      return item;
    })
    .call(sel => {
      sel.select('.swatch').style('background', d => d.color);
      sel.select('.key-text').text(d => d.label);
    });
}

// ============================================================
//  VIEW SWITCH + WIRING
// ============================================================

function setView(v) {
  state.view = v;
  el.chart.style.display     = v === 'chart' ? '' : 'none';
  el.tableWrap.style.display = v === 'table' ? 'block' : 'none';
  if (v === 'chart') renderChart();
  paint();
}

function wire() {
  d3.select('#colorMode').property('value', state.colorMode)
    .on('change', function () {
      hideTip();
      state.colorMode = this.value;
      renderPartyKey(); renderTable(); paint();
    });

  d3.select('#dotMode').property('value', state.dotMode)
    .on('change', function () {
      hideTip();
      state.dotMode = this.value;
      renderChart(); paint();
    });

  d3.select('#view').property('value', state.view)
    .on('change', function () { hideTip(); setView(this.value); });

  el.clearBtn.addEventListener('click', () => {
    clearBrushRect();
    state.selected.clear();
    paint();
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && state.selected.size) {
      clearBrushRect();
      state.selected.clear();
      paint();
    }
  });

  let pending;
  const onResize = () => {
    clearTimeout(pending);
    pending = setTimeout(() => { renderChart(); renderLegend(); paint(); }, 80);
  };
  new ResizeObserver(onResize).observe(el.chart);
  new ResizeObserver(onResize).observe(el.legendBox);
}

// ============================================================
//  BOOT
// ============================================================

Promise.all([d3.csv(DATA_FILE), d3.csv(PEOPLE_FILE)])
  .then(([ageRows, personRows]) => {
    shape(ageRows, personRows);
    el.loading.style.display = 'none';
    wire();
    renderPartyKey();
    renderChart();
    renderLegend();
    renderTable();
    paint();
  })
  .catch(err => {
    console.error(err);
    el.loading.className = 'err';
    el.loading.textContent =
      `Could not load ${DATA_FILE}. This page uses ES modules and fetch, so it has to be served over HTTP — ` +
      `run "python3 -m http.server 8000" in this folder and open http://localhost:8000.`;
  });
