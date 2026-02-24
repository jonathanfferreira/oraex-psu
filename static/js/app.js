/**
 * ORAEX PSU Manager — Main Application JS v2.0
 * Shared utilities, API calls, and common UI components
 */

// ══════════════════════════════════════════════════════════
//  API HELPERS
// ══════════════════════════════════════════════════════════

const API = {
    async get(url) {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`API error: ${resp.status}`);
        return resp.json();
    },

    async post(url, data) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!resp.ok) throw new Error(`API error: ${resp.status}`);
        return resp.json();
    },

    dashboard: (client = 'Todos') => API.get('/api/dashboard?client=' + encodeURIComponent(client)),
    servers: (params) => API.get('/api/servers?' + new URLSearchParams(params)),
    gmuds: (params) => API.get('/api/gmuds?' + new URLSearchParams(params)),
    cmdb: (params) => API.get('/api/cmdb?' + new URLSearchParams(params)),
    filters: () => API.get('/api/filters'),
    planning: () => API.get('/api/planning'),
    importData: () => API.post('/api/import', {}),
    generateTitle: (data) => API.post('/api/gmud/generate-title', data),
};


// ══════════════════════════════════════════════════════════
//  UI HELPERS
// ══════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}


function animateValue(el, start, end, duration = 1200) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (!el) return;
    const range = end - start;
    const startTime = performance.now();

    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
        const current = Math.round(start + range * eased);
        el.textContent = current.toLocaleString('pt-BR');
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}


function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
        return dateStr;
    }
}


function formatDateTime(dateStr) {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch {
        return dateStr;
    }
}


function getStatusBadge(status) {
    if (!status) return '<span class="status-badge">—</span>';
    const s = status.toLowerCase().trim();
    let cls = '';
    if (s.includes('encerrada') || s.includes('conclu')) cls = 'encerrada';
    else if (s.includes('implementar') || s.includes('em andamento')) cls = 'implementar';
    else if (s.includes('replanejar') || s.includes('replanejada')) cls = 'replanejar';
    else if (s.includes('cancel')) cls = 'cancelada';
    else if (s.includes('ativo') || s.includes('ativa')) cls = 'ativo';
    else if (s.includes('aberta') || s.includes('aberto')) cls = 'aberta';
    else cls = 'implementar';
    return `<span class="status-badge ${cls}">${status}</span>`;
}


function getEnvBadge(env) {
    if (!env) return '—';
    const e = env.toLowerCase().trim();
    let cls = 'dev';
    if (e.startsWith('prod') || e === 'p') cls = 'prod';
    else if (e.startsWith('hom') || e === 'h' || e === 'hml') cls = 'hml';
    else if (e.startsWith('trans') || e === 't') cls = 'prod';
    else if (e.startsWith('dev') || e === 'd' || e.startsWith('des')) cls = 'dev';
    return `<span class="env-badge ${cls}">${env}</span>`;
}


function getPsuBadge(version) {
    if (!version) return '—';
    let cls = 'outdated';
    // 19.30 and 19.29 are latest
    if (version.includes('19.30') || version.includes('19.29') || version.includes('19.28')) cls = 'latest';
    else if (version.includes('19.27') || version.includes('19.26')) cls = 'outdated';
    else cls = 'critical';
    return `<span class="psu-badge ${cls}">${version}</span>`;
}


function createPagination(data, onPageClick) {
    const { page, pages, total } = data;
    if (pages <= 1) return '';

    let html = '<div class="table-footer">';
    html += `<span class="table-info">Página ${page} de ${pages} (${total.toLocaleString('pt-BR')} registros)</span>`;
    html += '<div class="pagination">';

    html += `<button class="page-btn" ${page <= 1 ? 'disabled' : ''} onclick="${onPageClick}(${page - 1})">‹</button>`;

    const start = Math.max(1, page - 2);
    const end = Math.min(pages, page + 2);

    if (start > 1) {
        html += `<button class="page-btn" onclick="${onPageClick}(1)">1</button>`;
        if (start > 2) html += '<span class="page-btn" style="border:none;cursor:default">…</span>';
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="${onPageClick}(${i})">${i}</button>`;
    }

    if (end < pages) {
        if (end < pages - 1) html += '<span class="page-btn" style="border:none;cursor:default">…</span>';
        html += `<button class="page-btn" onclick="${onPageClick}(${pages})">${pages}</button>`;
    }

    html += `<button class="page-btn" ${page >= pages ? 'disabled' : ''} onclick="${onPageClick}(${page + 1})">›</button>`;
    html += '</div></div>';

    return html;
}


// ══════════════════════════════════════════════════════════
//  IMPORT
// ══════════════════════════════════════════════════════════

async function triggerImport() {
    const btn = document.getElementById('importBtn');
    const status = document.getElementById('importStatus');

    btn.disabled = true;
    btn.style.opacity = '0.5';
    status.textContent = 'Enviando...';
    status.style.color = 'var(--warning)';

    try {
        const result = await API.importData();

        if (result.task_id) {
            const taskId = result.task_id;
            status.textContent = '⚙️ Processando em 2º plano...';

            const pollInterval = setInterval(async () => {
                try {
                    const resp = await fetch(`/api/task-status/${taskId}`);
                    const taskData = await resp.json();

                    if (taskData.status === 'success') {
                        clearInterval(pollInterval);
                        status.textContent = '✅ Import concluído!';
                        status.style.color = 'var(--success)';
                        btn.disabled = false;
                        btn.style.opacity = '1';
                        showToast('Dados importados com sucesso! Recarregando...', 'success');
                        setTimeout(() => location.reload(), 1500);
                    } else if (taskData.status === 'error') {
                        clearInterval(pollInterval);
                        status.textContent = '❌ Erro no import!';
                        status.style.color = 'var(--danger)';
                        btn.disabled = false;
                        btn.style.opacity = '1';
                        showToast('Erro ao importar: ' + taskData.message, 'error');
                    }
                    // else 'processing' → wait next interval
                } catch (pollErr) {
                    console.error('Polling error:', pollErr);
                }
            }, 1500);
        } else {
            // Fallback: resposta síncrona legada
            status.textContent = result.status === 'success' ? '✅ Import concluído!' : '❌ Erro!';
            status.style.color = result.status === 'success' ? 'var(--success)' : 'var(--danger)';
            btn.disabled = false;
            btn.style.opacity = '1';
            if (result.status === 'success') setTimeout(() => location.reload(), 1500);
        }
    } catch (e) {
        status.textContent = 'Erro no import!';
        status.style.color = 'var(--danger)';
        btn.disabled = false;
        btn.style.opacity = '1';
        showToast('Erro ao importar: ' + e.message, 'error');
    }
}


// ══════════════════════════════════════════════════════════
//  LAST UPDATE
// ══════════════════════════════════════════════════════════

async function loadLastUpdate() {
    try {
        const data = await API.dashboard();
        const el = document.querySelector('#lastUpdate span');
        if (data.last_import) {
            el.textContent = 'Última importação: ' + formatDateTime(data.last_import.imported_at);
        } else {
            el.textContent = 'Nenhuma importação realizada';
        }
    } catch {
        // silent
    }
}

document.addEventListener('DOMContentLoaded', loadLastUpdate);


// ══════════════════════════════════════════════════════════
//  CHART.JS COLORS
// ══════════════════════════════════════════════════════════

const CHART_COLORS = {
    primary: '#0088ee',
    secondary: '#00bbff',
    tertiary: '#3b82f6',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    cyan: '#06b6d4',
    pink: '#ec4899',
    orange: '#f97316',
    lime: '#84cc16',
    palette: [
        '#0088ee', '#00bbff', '#3b82f6', '#10b981', '#f59e0b',
        '#ef4444', '#06b6d4', '#ec4899', '#f97316', '#84cc16',
        '#8b5cf6', '#14b8a6', '#eab308', '#f43f5e', '#0ea5e9'
    ],
    paletteBg: [
        'rgba(0,136,238,0.15)', 'rgba(0,187,255,0.15)', 'rgba(59,130,246,0.15)',
        'rgba(16,185,129,0.15)', 'rgba(245,158,11,0.15)', 'rgba(239,68,68,0.15)',
        'rgba(6,182,212,0.15)', 'rgba(236,72,153,0.15)', 'rgba(249,115,22,0.15)',
        'rgba(132,204,22,0.15)', 'rgba(139,92,246,0.15)', 'rgba(20,184,166,0.15)',
        'rgba(234,179,8,0.15)', 'rgba(244,63,94,0.15)', 'rgba(14,165,233,0.15)'
    ]
};


function applyChartDefaults() {
    if (typeof Chart === 'undefined') return;

    Chart.defaults.color = '#a0a0cc';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.pointStyleWidth = 8;
    Chart.defaults.plugins.legend.labels.padding = 14;
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(10, 10, 26, 0.95)';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.1)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.titleFont = { weight: '600', size: 12 };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 11 };
    Chart.defaults.elements.arc.borderWidth = 0;
    Chart.defaults.elements.bar.borderRadius = 4;
    Chart.defaults.scale.grid = { color: 'rgba(255,255,255,0.04)' };
}


// ══════════════════════════════════════════════════════════
//  UTILITIES
// ══════════════════════════════════════════════════════════

function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}


function exportCSV(apiUrl, params = {}) {
    const filtered = {};
    for (const [k, v] of Object.entries(params)) {
        if (v !== '' && v !== null && v !== undefined) filtered[k] = v;
    }
    const queryString = new URLSearchParams(filtered).toString();
    const url = queryString ? `${apiUrl}?${queryString}` : apiUrl;
    window.open(url, '_blank');
}


async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copiado para a área de transferência!', 'success');
    } catch {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Copiado!', 'success');
    }
}
