/**
 * Chart.js initialisation helpers for the Cyprus Water Levels dashboard.
 * Both functions return the Chart instance so callers can destroy/redraw
 * when the range selector changes.
 */

const SEVERITY_COLORS = {
    critical: '#ef4444',  // red-500
    warning:  '#f59e0b',  // amber-500
    healthy:  '#10b981',  // emerald-500
};

const CRITICAL_THRESHOLD = 20; // percent — used for dashed reference line

/**
 * Minimum data points per year to be considered "dense" (i.e. daily data).
 * Years with fewer points are sparse (monthly samples) — Day granularity
 * produces poor comparisons for these years.
 */
const SPARSE_YEAR_THRESHOLD = 50;

/**
 * Check whether a given year has sparse data (fewer points than threshold).
 * Sparse years should use Month granularity instead of Day for YoY comparison.
 * @param {Array<{date: string, value: number}>} data  Full dataset
 * @param {number} year  The year to check
 * @returns {boolean}  true if the year has fewer than SPARSE_YEAR_THRESHOLD points
 */
function isYearSparse(data, year) {
    let count = 0;
    for (const d of data) {
        if (new Date(d.date).getFullYear() === year) count++;
    }
    return count < SPARSE_YEAR_THRESHOLD;
}

/**
 * Show/hide the sparse-data hint and disable the Day granularity button when
 * either selected year has sparse data. Called whenever year selects change.
 * Shared by dashboard.html and dam_detail.html — defined here to avoid duplication.
 * @param {Array<{date: string, value: number}>} data  Full dataset
 * @param {string} selAId  ID of the "year A" <select> element
 * @param {string} selBId  ID of the "year B" <select> element
 * @param {string} granBtnSelector  CSS selector for granularity buttons
 * @param {string} hintId  ID of the sparse-data hint element
 */
function updateSparseWarning(data, selAId, selBId, granBtnSelector, hintId) {
    const yearA = parseInt(document.getElementById(selAId).value, 10);
    const yearB = parseInt(document.getElementById(selBId).value, 10);
    const sparse = isYearSparse(data, yearA) || isYearSparse(data, yearB);
    const hint = document.getElementById(hintId);
    if (hint) hint.style.display = sparse ? 'inline' : 'none';
    document.querySelectorAll(granBtnSelector).forEach(btn => {
        if (btn.textContent.trim().toLowerCase() === 'day') {
            btn.disabled = sparse;
            btn.style.opacity = sparse ? '0.4' : '1';
            btn.style.cursor = sparse ? 'not-allowed' : 'pointer';
        }
    });
}

/**
 * Convert the [{date, value}] format from the server to Chart.js {x, y} points.
 * @param {Array<{date: string, value: number}>} data
 * @returns {Array<{x: string, y: number}>}
 */
function toChartPoints(data) {
    return data.map(d => ({ x: d.date, y: d.value }));
}

/**
 * Shared Chart.js scale + plugin configuration.
 * @param {string} color  Hex color for border + fill
 * @returns {object}  Chart.js options object
 */
function buildChartOptions(color) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
            x: {
                type: 'time',
                time: { unit: 'month', tooltipFormat: 'MMM yyyy' },
                grid: { display: false },
                ticks: { color: '#94a3b8', maxTicksLimit: 12 },
            },
            y: {
                min: 0,
                max: 100,
                ticks: {
                    color: '#94a3b8',
                    callback: v => v + '%',
                },
                grid: { color: '#f1f5f9' },
            },
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#1e293b',
                titleColor: '#94a3b8',
                bodyColor: '#f8fafc',
                padding: 10,
                callbacks: {
                    label: ctx => ` ${ctx.parsed.y.toFixed(1)}%`,
                },
            },
        },
    };
}

/**
 * Initialise the system-wide historical capacity trend chart.
 * @param {string} canvasId
 * @param {Array<{date: string, value: number}>} data
 * @returns {Chart|null}
 */
function initSystemChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !data || data.length === 0) return null;

    const color = '#3b82f6'; // blue-500

    return new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'System Capacity %',
                data: toChartPoints(data),
                borderColor: color,
                backgroundColor: color + '1a',  // 10% opacity
                borderWidth: 2,
                fill: true,
                pointRadius: 0,
                pointHitRadius: 10,
                tension: 0.3,
            }],
        },
        options: buildChartOptions(color),
    });
}

/**
 * Initialise a per-dam historical capacity chart. Color matches severity.
 * @param {string} canvasId
 * @param {Array<{date: string, value: number}>} data
 * @param {string} severity  'critical' | 'warning' | 'healthy'
 * @returns {Chart|null}
 */
function initDamChart(canvasId, data, severity) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !data || data.length === 0) return null;

    const color = SEVERITY_COLORS[severity] || SEVERITY_COLORS.healthy;

    return new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Capacity %',
                data: toChartPoints(data),
                borderColor: color,
                backgroundColor: color + '1a',
                borderWidth: 2,
                fill: true,
                pointRadius: 0,
                pointHitRadius: 10,
                tension: 0.3,
            }],
        },
        options: buildChartOptions(color),
    });
}

// ── Two-Year Comparison chart ──────────────────────────────────────────

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Extract sorted unique years from [{date, value}] data.
 * @param {Array<{date: string, value: number}>} data
 * @returns {number[]}  descending order (newest first)
 */
function getAvailableYears(data) {
    const years = new Set();
    for (const d of data) years.add(new Date(d.date).getFullYear());
    return Array.from(years).sort((a, b) => b - a);
}

/**
 * Filter data to a single year and normalise dates to reference year 2000.
 * @param {Array<{date: string, value: number}>} data
 * @param {number} year
 * @returns {Array<{x: string, y: number}>}
 */
function filterYear(data, year) {
    const points = [];
    for (const d of data) {
        const dt = new Date(d.date);
        if (dt.getFullYear() !== year) continue;
        const norm = `2000-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
        points.push({ x: norm, y: d.value });
    }
    return points;
}

/**
 * Aggregate [{x: '2000-MM-DD', y}] by granularity.
 * - 'day':   pass through unchanged
 * - 'month': average per calendar month → 12 points (labelled Jan–Dec)
 * - 'year':  single average across all points
 * @param {Array<{x: string, y: number}>} points
 * @param {'day'|'month'|'year'} granularity
 * @returns {Array<{x: string, y: number}>}
 */
function aggregateByGranularity(points, granularity) {
    if (granularity === 'day') return points;

    if (granularity === 'month') {
        const buckets = new Map(); // month (0-11) → [values]
        for (const p of points) {
            const m = new Date(p.x).getMonth();
            if (!buckets.has(m)) buckets.set(m, []);
            buckets.get(m).push(p.y);
        }
        const result = [];
        for (const [m, vals] of Array.from(buckets.entries()).sort((a, b) => a[0] - b[0])) {
            const avg = vals.reduce((s, v) => s + v, 0) / vals.length;
            result.push({ x: MONTH_LABELS[m], y: Math.round(avg * 10) / 10 });
        }
        return result;
    }

    // 'year' granularity — single point
    if (points.length === 0) return [];
    const avg = points.reduce((s, p) => s + p.y, 0) / points.length;
    return [{ x: 'Avg', y: Math.round(avg * 10) / 10 }];
}

/**
 * Compute per-point difference (A - B) with colour coding.
 * @param {Array<{x: string, y: number}>} seriesA
 * @param {Array<{x: string, y: number}>} seriesB
 * @returns {{data: Array<{x: string, y: number}>, colors: string[]}}
 */
function computeDifference(seriesA, seriesB) {
    const mapB = new Map();
    for (const p of seriesB) mapB.set(p.x, p.y);

    const data = [];
    const colors = [];
    for (const p of seriesA) {
        const bVal = mapB.get(p.x);
        if (bVal === undefined) continue;
        const diff = Math.round((p.y - bVal) * 10) / 10;
        data.push({ x: p.x, y: diff });
        colors.push(diff >= 0 ? '#10b98166' : '#ef444466'); // emerald/red with alpha
    }
    return { data, colors };
}

/**
 * Initialise a two-year comparison chart (mixed bar + line).
 * @param {string} canvasId
 * @param {Array<{date: string, value: number}>} data  Full dataset
 * @param {number} yearA  Primary year (shown as solid line)
 * @param {number} yearB  Comparison year (shown as dashed line)
 * @param {'day'|'month'|'year'} granularity
 * @returns {Chart|null}
 */
function initComparisonChart(canvasId, data, yearA, yearB, granularity) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !data || data.length === 0) return null;

    const rawA = filterYear(data, yearA);
    const rawB = filterYear(data, yearB);
    const aggA = aggregateByGranularity(rawA, granularity);
    const aggB = aggregateByGranularity(rawB, granularity);
    const diff = computeDifference(aggA, aggB);

    const useTimeAxis = granularity === 'day';
    const labels = useTimeAxis ? undefined : aggA.map(p => p.x);

    const datasets = [
        {
            type: 'line',
            label: String(yearA),
            data: aggA,
            borderColor: '#3b82f6',
            backgroundColor: '#3b82f61a',
            borderWidth: 3,
            fill: false,
            pointRadius: granularity === 'day' ? 0 : 4,
            pointHitRadius: 10,
            tension: 0.3,
            yAxisID: 'y',
            order: 1,
        },
        {
            type: 'line',
            label: String(yearB),
            data: aggB,
            borderColor: '#94a3b8',
            backgroundColor: '#94a3b81a',
            borderWidth: 2,
            borderDash: [6, 3],
            fill: false,
            pointRadius: granularity === 'day' ? 0 : 3,
            pointHitRadius: 10,
            tension: 0.3,
            yAxisID: 'y',
            order: 2,
        },
        {
            type: 'bar',
            label: 'Difference',
            data: diff.data,
            backgroundColor: diff.colors,
            borderColor: diff.colors.map(c => c.replace('66', 'cc')),
            borderWidth: 1,
            borderRadius: 3,
            yAxisID: 'y2',
            order: 3,
            barPercentage: 0.6,
        },
    ];

    const xScale = useTimeAxis
        ? {
            type: 'time',
            time: { unit: 'month', tooltipFormat: 'dd MMM', displayFormats: { month: 'MMM' } },
            grid: { display: false },
            ticks: { color: '#94a3b8', maxTicksLimit: 12 },
        }
        : {
            type: 'category',
            grid: { display: false },
            ticks: { color: '#94a3b8' },
        };

    // Compute sensible y2 range — symmetric around 0
    const maxAbsDiff = diff.data.reduce((m, p) => Math.max(m, Math.abs(p.y)), 0);
    const y2Limit = Math.max(Math.ceil(maxAbsDiff / 5) * 5, 10);

    return new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: xScale,
                y: {
                    position: 'left',
                    min: 0,
                    max: 100,
                    ticks: { color: '#94a3b8', callback: v => v + '%' },
                    grid: { color: '#f1f5f9' },
                    title: { display: true, text: 'Capacity %', color: '#94a3b8', font: { size: 11 } },
                },
                y2: {
                    position: 'right',
                    min: -y2Limit,
                    max: y2Limit,
                    ticks: {
                        color: '#94a3b8',
                        callback: v => (v > 0 ? '+' : '') + v + 'pp',
                    },
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: 'Difference (pp)', color: '#94a3b8', font: { size: 11 } },
                },
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { usePointStyle: true, boxWidth: 30, color: '#475569', font: { size: 11 } },
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#94a3b8',
                    bodyColor: '#f8fafc',
                    padding: 10,
                    callbacks: {
                        title: items => {
                            if (!items.length) return '';
                            if (useTimeAxis) {
                                const d = new Date(items[0].parsed.x);
                                return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
                            }
                            return items[0].label;
                        },
                        label: item => {
                            if (item.dataset.label === 'Difference') {
                                const v = item.parsed.y;
                                return ` Diff: ${v > 0 ? '+' : ''}${v.toFixed(1)}pp`;
                            }
                            return ` ${item.dataset.label}: ${item.parsed.y.toFixed(1)}%`;
                        },
                    },
                },
            },
        },
    });
}
