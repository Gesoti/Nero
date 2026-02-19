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
