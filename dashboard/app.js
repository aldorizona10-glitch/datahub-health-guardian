/**
 * DataHub Health Guardian — Dashboard App
 * Fetches scan data from FastAPI backend and renders interactive dashboard
 */

const API_BASE = 'http://localhost:8000';

// ─── State ───
let currentScan = null;

// ─── Init ───
document.addEventListener('DOMContentLoaded', () => {
    // Add SVG gradient for score ring
    const svg = document.querySelector('.score-ring');
    if (svg) {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.id = 'scoreGradient';
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '100%');

        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('style', 'stop-color:#6366f1');

        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('style', 'stop-color:#8b5cf6');

        gradient.appendChild(stop1);
        gradient.appendChild(stop2);
        defs.appendChild(gradient);
        svg.prepend(defs);
    }

    // Theme toggling
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            document.documentElement.setAttribute('data-theme', isLight ? 'dark' : 'light');
        });
    }

    // Auto-load demo data
    loadDemoData();
});

// ─── API Calls ───
async function runScan() {
    const btn = document.getElementById('scanBtn');
    btn.classList.add('scanning');
    btn.innerHTML = '<span class="btn-icon">⏳</span> Scanning...';

    try {
        const resp = await fetch(`${API_BASE}/api/scan?demo=true`, { method: 'POST' });
        if (resp.ok) {
            currentScan = await resp.json();
            renderDashboard(currentScan);
        } else {
            // Fallback to demo data
            loadDemoData();
        }
    } catch {
        loadDemoData();
    }

    btn.classList.remove('scanning');
    btn.innerHTML = '<span class="btn-icon">⚡</span> Run Scan';
}

function loadDemoData() {
    // Built-in demo data — no server needed
    currentScan = getDemoData();
    renderDashboard(currentScan);
}

// ─── Render ───
function renderDashboard(data) {
    const scan = data.scan;
    const analysis = data.analysis;
    const lineage = data.lineage_impacts;

    // Health Score
    animateScore(scan.summary?.health_score ?? 62);

    // Stats
    animateCounter('datasetsScanned', scan.datasets_scanned || 7);
    animateCounter('criticalCount', scan.by_severity?.critical || 4);
    animateCounter('warningCount', scan.by_severity?.warning || 3);
    animateCounter('infoCount', scan.by_severity?.info || 1);

    // Risk Badge
    const riskBadge = document.getElementById('riskBadge');
    const risk = analysis.risk_level || 'high';
    riskBadge.textContent = risk.toUpperCase();
    riskBadge.className = `risk-badge ${risk}`;

    // AI Analysis
    document.getElementById('executiveSummary').innerHTML =
        `<p>${analysis.executive_summary || 'Analysis complete.'}</p>`;
    document.getElementById('analysisCard').classList.add('fade-in');

    // Priorities
    renderPriorities(analysis.top_priorities || []);

    // Dataset Grid
    renderDatasetGrid();

    // Lineage
    renderLineageCards(lineage || {});

    // Quick Wins
    renderQuickWins(analysis.quick_wins || []);

    // Report
    document.getElementById('reportCard').textContent = data.report || 'Report generated.';
}

function animateScore(score) {
    const ring = document.getElementById('scoreRing');
    const valueEl = document.getElementById('healthScore');
    const circumference = 2 * Math.PI * 52; // r=52

    // Set stroke color based on score
    let color1 = '#ef4444', color2 = '#f59e0b';
    if (score >= 80) { color1 = '#10b981'; color2 = '#06d6a0'; }
    else if (score >= 50) { color1 = '#f59e0b'; color2 = '#fbbf24'; }

    // Update gradient colors
    const stops = document.querySelectorAll('#scoreGradient stop');
    if (stops.length >= 2) {
        stops[0].style.stopColor = color1;
        stops[1].style.stopColor = color2;
    }

    // Animate ring
    const offset = circumference - (score / 100) * circumference;
    ring.style.strokeDasharray = circumference;
    setTimeout(() => {
        ring.style.strokeDashoffset = offset;
    }, 100);

    // Animate number
    let current = 0;
    const step = score / 40;
    const interval = setInterval(() => {
        current += step;
        if (current >= score) {
            current = score;
            clearInterval(interval);
        }
        valueEl.textContent = Math.round(current) + '%';
    }, 25);
}

function animateCounter(id, target) {
    const el = document.getElementById(id);
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 30));
    const interval = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(interval);
        }
        el.textContent = current;
    }, 30);
}

function renderPriorities(priorities) {
    const container = document.getElementById('prioritiesList');
    if (!priorities.length) {
        container.innerHTML = '<div class="glass-card" style="padding:20px;color:var(--text-muted)">No priorities found</div>';
        return;
    }

    container.innerHTML = priorities.map(p => `
        <div class="priority-card glass-card fade-in">
            <div class="priority-rank">${p.rank}</div>
            <div class="priority-content">
                <h3>${escapeHtml(p.dataset)}</h3>
                <div class="priority-issue">${escapeHtml(p.issue)}</div>
                <div class="priority-impact">⚡ ${escapeHtml(p.business_impact)}</div>
            </div>
            <div class="priority-action">${escapeHtml(p.recommended_action?.split(' ').slice(0, 4).join(' ') || 'Fix')}...</div>
        </div>
    `).join('');
}

function renderDatasetGrid() {
    const datasets = [
        { name: 'healthcare.patients', platform: 'postgres', status: 'critical', score: 30 },
        { name: 'nyc_taxi.trips', platform: 'snowflake', status: 'warning', score: 55 },
        { name: 'retail.orders', platform: 'bigquery', status: 'warning', score: 60 },
        { name: 'events.clickstream', platform: 'kafka', status: 'critical', score: 25 },
        { name: 'finance.transactions', platform: 'mysql', status: 'healthy', score: 100 },
        { name: 'logs.application', platform: 's3', status: 'critical', score: 35 },
        { name: 'warehouse.inventory', platform: 'hive', status: 'info', score: 80 },
    ];

    const container = document.getElementById('datasetGrid');
    container.innerHTML = datasets.map((d, i) => `
        <div class="dataset-card glass-card ${d.status} fade-in" style="animation-delay: ${i * 0.05}s">
            <div class="dataset-name">${d.name}</div>
            <div class="dataset-platform">${d.platform}</div>
            <div class="dataset-score ${d.status}">${d.score}%</div>
        </div>
    `).join('');
}

function renderLineageCards(impacts) {
    const container = document.getElementById('lineageCards');
    const entries = Object.entries(impacts);

    if (!entries.length) {
        container.innerHTML = '<div class="glass-card" style="padding:20px;color:var(--text-muted)">No lineage impact data</div>';
        return;
    }

    container.innerHTML = entries.map(([urn, data]) => {
        const name = urn.split(',')[1] || urn;
        const systems = (data.affected_systems || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
        const steps = (data.mitigation_steps || []).map(s => `<li>${escapeHtml(s.replace(/^\d+\.\s*/, ''))}</li>`).join('');

        return `
            <div class="lineage-card glass-card fade-in">
                <div class="lineage-header">
                    <div class="lineage-title">${escapeHtml(name)}</div>
                    <div class="blast-badge ${data.blast_radius || 'medium'}">${(data.blast_radius || 'unknown').toUpperCase()}</div>
                </div>
                <div class="lineage-summary">${escapeHtml(data.impact_summary || '')}</div>
                ${systems ? `<div style="margin-bottom:8px;font-size:12px;font-weight:600;color:var(--text-primary)">Affected Systems</div><ul class="lineage-systems">${systems}</ul>` : ''}
                ${steps ? `<div style="margin-bottom:8px;font-size:12px;font-weight:600;color:var(--text-primary)">Mitigation Steps</div><ol class="lineage-steps">${steps}</ol>` : ''}
            </div>
        `;
    }).join('');
}

function renderQuickWins(wins) {
    const container = document.getElementById('quickWinsList');
    if (!wins.length) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:8px">No quick wins identified</p>';
        return;
    }

    container.innerHTML = wins.map((w, i) => `
        <div class="quickwin-item fade-in" style="animation-delay:${i * 0.05}s">
            <div class="quickwin-check" onclick="this.classList.toggle('checked')"></div>
            <span>${escapeHtml(w)}</span>
        </div>
    `).join('');
}

// ─── Utilities ───
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Demo Data (self-contained, no server needed) ───
function getDemoData() {
    return {
        scan: {
            scan_id: "demo-001",
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            datasets_scanned: 7,
            total_issues: 8,
            by_severity: { critical: 4, warning: 3, info: 1 },
            summary: { health_score: 62, by_category: { governance: 3, documentation: 2, freshness: 1, classification: 1, lifecycle: 1 } },
            issues: []
        },
        analysis: {
            executive_summary: "The data ecosystem has significant governance gaps. 4 critical issues require immediate attention, primarily around missing ownership for sensitive datasets and a deprecated dataset with active consumers. Quick wins in documentation can rapidly improve the health score.",
            risk_level: "high",
            top_priorities: [
                { rank: 1, dataset: "healthcare.patients", issue: "No owner + No PII classification on patient records", business_impact: "HIPAA compliance risk — unclassified PII data without an accountable owner", recommended_action: "Immediately assign a data steward and add PII/HIPAA tags" },
                { rank: 2, dataset: "events.clickstream", issue: "Deprecated with 8 active downstream consumers", business_impact: "When decommissioned, 8 downstream pipelines will break", recommended_action: "Notify consumer teams, create migration plan with deadline" },
                { rank: 3, dataset: "logs.application", issue: "No owner and no documentation", business_impact: "During incidents, nobody knows who to contact", recommended_action: "Assign SRE team ownership, document log format" },
                { rank: 4, dataset: "nyc_taxi.trips", issue: "127 days since last update", business_impact: "Downstream analytics using stale data", recommended_action: "Verify ETL pipeline health, check for failures" }
            ],
            quick_wins: [
                "Add descriptions to 'logs.application' and 'retail.orders' (15 min each)",
                "Tag 'healthcare.patients' with PII/HIPAA classifications (5 min)",
                "Add domain tags to 'warehouse.inventory' (5 min)",
                "Document the 12 undocumented fields in 'retail.orders' (30 min)"
            ],
            trend_assessment: "Ecosystem shows rapid growth without governance. Recommend data stewardship program."
        },
        lineage_impacts: {
            "urn:li:dataset:(urn:li:dataPlatform:kafka,events.clickstream,PROD)": {
                downstream_count: 8,
                blast_radius: "high",
                impact_summary: "8 downstream consumers spanning analytics, ML features, and real-time dashboards will lose data when this deprecated source is decommissioned",
                affected_systems: ["analytics.user_behavior (BigQuery)", "ml.recommendation_features (Snowflake)", "dashboard.realtime_metrics (Druid)", "reports.weekly_engagement (Hive)"],
                mitigation_steps: ["1. Inventory all 8 downstream consumers with their SLAs", "2. Notify owning teams with 30-day deadline", "3. Provide replacement data source docs", "4. Set up dual-write period", "5. Monitor consumer migration weekly"]
            },
            "urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)": {
                downstream_count: 3,
                blast_radius: "medium",
                impact_summary: "Patient data flows to 3 downstream systems. Missing PII classification means downstream datasets may also be untagged, creating compliance exposure",
                affected_systems: ["analytics.patient_outcomes (BigQuery)", "ml.readmission_risk (Vertex AI)", "reports.monthly_clinical (Looker)"],
                mitigation_steps: ["1. Immediately tag source with PII/HIPAA", "2. Propagate tags to downstream datasets", "3. Audit access controls", "4. Assign data steward"]
            }
        },
        report: `# 🏥 DataHub Health Report\n\n## Executive Summary\nThe data ecosystem has **significant governance gaps**. 4 critical issues require immediate attention.\n\n## 📊 Health Score: 62% | Risk Level: 🔴 HIGH\n\n## ❌ Critical Issues\n| # | Dataset | Issue |\n|---|---------|-------|\n| 1 | healthcare.patients | No owner + No PII tags |\n| 2 | events.clickstream | Deprecated, 8 consumers |\n| 3 | logs.application | No owner, no docs |\n| 4 | healthcare.patients | PII without classification |\n\n## 🎯 Recommended Actions\n1. [URGENT] Assign data steward to healthcare.patients\n2. [URGENT] Create migration plan for events.clickstream\n3. [HIGH] Assign SRE ownership to logs.application\n4. [MEDIUM] Investigate stale nyc_taxi.trips pipeline\n\n---\n*Generated by DataHub Health Guardian Agent*`,
        timestamp: new Date().toISOString()
    };
}
