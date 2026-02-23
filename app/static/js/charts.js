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

// ── Year-on-Year comparison chart ──────────────────────────────────────────

/** Palette for year lines — newest year gets the first (boldest) color. */
const YOY_COLORS = [
    '#3b82f6', // blue-500    (current year)
    '#ef4444', // red-500
    '#10b981', // emerald-500
    '#f59e0b', // amber-500
    '#8b5cf6', // violet-500
    '#ec4899', // pink-500
    '#06b6d4', // cyan-500
    '#84cc16', // lime-500
    '#f97316', // orange-500
];

/**
 * Group [{date, value}] by calendar year and normalise all dates to
 * a common reference year (2000) so Chart.js overlays them on one axis.
 * @param {Array<{date: string, value: number}>} data
 * @returns {Map<number, Array<{x: string, y: number}>>}  year → points
 */
function groupByYear(data) {
    const groups = new Map();
    for (const d of data) {
        const dt = new Date(d.date);
        const year = dt.getFullYear();
        // Normalise to year 2000 so all years share the same x-axis
        const norm = `2000-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
        if (!groups.has(year)) groups.set(year, []);
        groups.get(year).push({ x: norm, y: d.value });
    }
    return groups;
}

/**
 * Initialise a year-on-year overlay chart.
 * Each year is a separate line, x-axis shows Jan–Dec.
 * @param {string} canvasId
 * @param {Array<{date: string, value: number}>} data
 * @returns {Chart|null}
 */
function initYoYChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !data || data.length === 0) return null;

    const groups = groupByYear(data);
    const years = Array.from(groups.keys()).sort((a, b) => b - a); // newest first

    const datasets = years.map((year, i) => {
        const color = YOY_COLORS[i % YOY_COLORS.length];
        const isCurrentYear = i === 0;
        return {
            label: String(year),
            data: groups.get(year),
            borderColor: color,
            backgroundColor: color + '1a',
            borderWidth: isCurrentYear ? 3 : 1.5,
            fill: false,
            pointRadius: 0,
            pointHitRadius: 10,
            tension: 0.3,
            borderDash: isCurrentYear ? [] : [4, 2],
        };
    });

    return new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'month', tooltipFormat: 'dd MMM', displayFormats: { month: 'MMM' } },
                    grid: { display: false },
                    ticks: { color: '#94a3b8', maxTicksLimit: 12 },
                },
                y: {
                    min: 0,
                    max: 100,
                    ticks: { color: '#94a3b8', callback: v => v + '%' },
                    grid: { color: '#f1f5f9' },
                },
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'line', boxWidth: 30, color: '#475569', font: { size: 11 } },
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#94a3b8',
                    bodyColor: '#f8fafc',
                    padding: 10,
                    callbacks: {
                        title: ctx => {
                            if (!ctx.length) return '';
                            // Show "15 Mar" without the reference year
                            const d = new Date(ctx[0].parsed.x);
                            return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
                        },
                        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}%`,
                    },
                },
            },
        },
    });
}
