// Renders data/report.json. No framework, no build step. All text from the
// data goes in through textContent.

const SOURCES = {
  arbeitnow: ['Arbeitnow', 'https://www.arbeitnow.com'],
  remotive: ['Remotive', 'https://remotive.com'],
}
const SENIORITY = ['intern', 'junior', 'mid', 'senior', 'lead', 'unknown']
const SENIORITY_LABEL = { intern: 'Intern', junior: 'Junior', mid: 'Mid-level', senior: 'Senior', lead: 'Lead / staff', unknown: 'Not stated' }
const MODE_LABEL = { remote: 'Remote', hybrid: 'Hybrid', onsite: 'On site', unknown: 'Not stated' }

const $ = (id) => document.getElementById(id)
const pct = (x, digits = 0) => `${(x * 100).toFixed(digits)}%`
const num = (x) => x.toLocaleString('en-US')

function el(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

// ---------- tooltip ----------

const tip = $('tooltip')

function showTip(event, value, label) {
  tip.replaceChildren(el('strong', '', value), el('span', '', label))
  tip.hidden = false
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX ?? rect.left + rect.width / 2
  const y = event.clientY ?? rect.top
  tip.style.left = `${Math.min(x + 12, innerWidth - tip.offsetWidth - 8)}px`
  tip.style.top = `${y - tip.offsetHeight - 10}px`
}

function hideTip() {
  tip.hidden = true
}

function withTip(node, value, label) {
  node.tabIndex = 0
  node.setAttribute('aria-label', `${label}: ${value}`)
  node.addEventListener('pointermove', (e) => showTip(e, value, label))
  node.addEventListener('focus', (e) => showTip(e, value, label))
  node.addEventListener('pointerleave', hideTip)
  node.addEventListener('blur', hideTip)
}

// ---------- pieces ----------

function bars(container, rows) {
  container.replaceChildren()
  if (!rows.length) {
    container.append(el('p', 'empty', 'Nothing yet.'))
    return
  }
  const max = Math.max(...rows.map((r) => r.value))
  for (const row of rows) {
    const label = el('div', 'bar-label', row.label)
    label.title = row.label
    const track = el('div', 'bar-track')
    const bar = el('div', `bar${row.quiet ? ' quiet' : ''}`)
    bar.style.width = `${max ? (row.value / max) * 100 : 0}%`
    track.append(bar)
    withTip(track, row.tip ?? row.text, row.tipLabel ?? row.label)
    const value = el('div', 'bar-value', row.text)
    container.append(label, track, value)
  }
}

function kpi(value, label) {
  const node = el('div', 'kpi')
  node.append(el('div', 'kpi-value', value), el('div', 'kpi-label', label))
  return node
}

function sparkline(weeks, shares, skill, max) {
  const W = 220
  const H = 64
  const pad = 4
  const x = (i) => (weeks.length === 1 ? W / 2 : pad + (i * (W - 2 * pad)) / (weeks.length - 1))
  const y = (v) => H - pad - (v / max) * (H - 2 * pad)
  const ns = 'http://www.w3.org/2000/svg'
  const svg = document.createElementNS(ns, 'svg')
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`)
  svg.setAttribute('class', 'spark')
  svg.setAttribute('role', 'img')
  svg.setAttribute('aria-label', `${skill}: ${shares.map((s, i) => `${weeks[i].week} ${pct(s)}`).join(', ')}`)
  const add = (tag, attrs) => {
    const node = document.createElementNS(ns, tag)
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v)
    svg.append(node)
    return node
  }
  add('line', { class: 'grid', x1: 0, x2: W, y1: H - pad, y2: H - pad })
  const points = shares.map((s, i) => `${x(i)},${y(s)}`)
  add('path', { class: 'area', d: `M${x(0)},${H - pad} L${points.join(' L')} L${x(shares.length - 1)},${H - pad} Z` })
  add('polyline', { class: 'line', points: points.join(' ') })
  const last = shares.length - 1
  add('circle', { class: 'end', cx: x(last), cy: y(shares[last]), r: 4 })
  const cross = add('line', { class: 'cross', y1: 0, y2: H, visibility: 'hidden' })

  // crosshair: snap to the nearest week
  svg.addEventListener('pointermove', (event) => {
    const box = svg.getBoundingClientRect()
    const px = ((event.clientX - box.left) / box.width) * W
    let i = 0
    for (let j = 1; j < weeks.length; j++) if (Math.abs(x(j) - px) < Math.abs(x(i) - px)) i = j
    cross.setAttribute('x1', x(i))
    cross.setAttribute('x2', x(i))
    cross.setAttribute('visibility', 'visible')
    showTip({ currentTarget: svg, clientX: event.clientX, clientY: box.top }, pct(shares[i], 1), `${skill}, week of ${formatDate(weeks[i].week)}`)
  })
  svg.addEventListener('pointerleave', () => {
    cross.setAttribute('visibility', 'hidden')
    hideTip()
  })
  return svg
}

function formatDate(day) {
  return new Date(`${day}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

function money(value, currency) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0, notation: 'compact' }).format(value)
}

// ---------- sections ----------

function renderTrend(trend) {
  const container = $('trend')
  container.replaceChildren()
  if (!trend.weeks.length) {
    container.append(el('p', 'empty', 'Trends appear after a few weeks of data.'))
    return
  }
  // one shared scale, so a flat 5% line doesn't look as dramatic as a 50% one
  const max = Math.max(...trend.series.flatMap((s) => s.share), 0.01)
  for (const series of trend.series) {
    const box = el('div', 'multiple')
    const title = el('h3', '', series.skill)
    title.append(el('span', '', pct(series.share.at(-1))))
    const axis = el('div', 'spark-axis')
    axis.append(el('span', '', formatDate(trend.weeks[0].week)), el('span', '', formatDate(trend.weeks.at(-1).week)))
    box.append(title, sparkline(trend.weeks, series.share, series.skill, max), axis)
    container.append(box)
  }
}

function renderPairs(report) {
  const select = $('pair-skill')
  const counts = new Map(report.top_skills.map((s) => [s.skill, s.postings]))
  for (const s of report.top_skills) select.append(new Option(s.skill, s.skill))
  const draw = () => {
    const skill = select.value
    const total = counts.get(skill) ?? 0
    const rows = report.pairs
      .filter((p) => p.a === skill || p.b === skill)
      .map((p) => ({ other: p.a === skill ? p.b : p.a, n: p.postings }))
      .sort((a, b) => b.n - a.n)
      .slice(0, 12)
      .map(({ other, n }) => ({
        label: other,
        value: n,
        text: pct(n / total),
        tip: `${n} of ${total}`,
        tipLabel: `${skill} postings that also mention ${other}`,
      }))
    bars($('pairs'), rows)
  }
  select.addEventListener('change', draw)
  if (report.top_skills.length) draw()
}

function renderSalaries(salaries) {
  const currencies = Object.entries(salaries)
  if (!currencies.length) return
  $('salary-block').hidden = false
  const container = $('salaries')
  for (const [currency, data] of currencies) {
    const block = el('div', 'currency')
    block.append(el('h3', '', `${currency}, ${data.postings} postings`))
    const grid = el('div', 'ranges')
    const rows = [{ skill: 'All postings', postings: data.postings, median: data.median, p25: data.p25, p75: data.p75 }, ...data.by_skill.slice(0, 10)]
    // a dot plot doesn't need a zero baseline; start near the lowest value so differences are visible
    const hi = Math.max(...rows.map((r) => r.p75 ?? r.median))
    const lo = Math.min(...rows.map((r) => r.p25 ?? r.median))
    const min = Math.max(0, lo - (hi - lo) * 0.15)
    const max = hi + (hi - lo) * 0.1
    const at = (v) => `${((v - min) / (max - min)) * 100}%`
    for (const row of rows) {
      const track = el('div', 'range-track')
      if (row.p25 !== undefined) {
        const range = el('div', 'range')
        range.style.left = at(row.p25)
        range.style.width = `${((row.p75 - row.p25) / (max - min)) * 100}%`
        const median = el('div', 'median')
        median.style.left = at(row.median)
        track.append(range, median)
      } else {
        const dot = el('div', 'dot')
        dot.style.left = at(row.median)
        track.append(dot)
      }
      withTip(track, money(row.median, currency), `${row.skill}, median of ${row.postings} postings`)
      grid.append(el('div', 'bar-label', row.skill), track, el('div', 'bar-value', money(row.median, currency)))
    }
    block.append(grid)
    container.append(block)
  }
}

function render(report) {
  const s = report.summary
  $('as-of').textContent = report.as_of
    ? `Updated ${new Date(`${report.as_of}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}`
    : 'No data yet'
  if (!report.as_of) return

  $('kpis').replaceChildren(
    kpi(num(s.active), `open postings in the last ${report.active_days} days`),
    kpi(num(s.new_this_week), 'new this week'),
    kpi(num(s.companies), 'companies hiring'),
    kpi(pct(s.remote_share), 'fully remote'),
    kpi(pct(s.salary_share), 'state a salary'),
  )

  $('skills-note').textContent = `Share of ${num(s.active)} open postings`
  bars(
    $('top-skills'),
    report.top_skills.slice(0, 20).map((r) => ({
      label: r.skill,
      value: r.postings,
      text: pct(r.share),
      tip: `${num(r.postings)} postings`,
      tipLabel: `${r.skill} (${r.category})`,
    })),
  )

  renderTrend(report.trend)
  renderPairs(report)

  const total = (rows) => rows.reduce((sum, r) => sum + r.postings, 0)
  const seniorityTotal = total(report.seniority)
  bars(
    $('seniority'),
    [...report.seniority]
      .sort((a, b) => SENIORITY.indexOf(a.key) - SENIORITY.indexOf(b.key))
      .map((r) => ({ label: SENIORITY_LABEL[r.key] ?? r.key, value: r.postings, text: pct(r.postings / seniorityTotal), tip: `${num(r.postings)} postings`, quiet: r.key === 'unknown' })),
  )
  const modeTotal = total(report.work_mode)
  bars(
    $('work-mode'),
    report.work_mode.map((r) => ({ label: MODE_LABEL[r.key] ?? r.key, value: r.postings, text: pct(r.postings / modeTotal), tip: `${num(r.postings)} postings`, quiet: r.key === 'unknown' })),
  )

  renderSalaries(report.salaries)
  bars(
    $('companies'),
    report.companies.map((r) => ({ label: r.company, value: r.postings, text: num(r.postings), tip: `${num(r.postings)} open postings` })),
  )

  const sources = $('sources')
  sources.append('Postings from ')
  report.sources.forEach((src, i) => {
    const [name, url] = SOURCES[src.source] ?? [src.source, null]
    if (i > 0) sources.append(i === report.sources.length - 1 ? ' and ' : ', ')
    if (url) {
      const link = el('a', '', name)
      link.href = url
      sources.append(link)
    } else sources.append(name)
  })
  sources.append('. Each posting stays on its original site; this page only counts.')
}

fetch('data/report.json')
  .then((r) => {
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })
  .then(render)
  .catch(() => {
    $('as-of').textContent = 'Could not load data/report.json'
  })
