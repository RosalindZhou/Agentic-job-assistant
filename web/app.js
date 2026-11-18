const state = {
    jobs: [],
    filteredJobs: []
};

// DOM Elements
const container = document.getElementById('jobs-container');
const statCount = document.getElementById('stat-count');
const refreshBtn = document.getElementById('refresh-btn');

const inputLocation = document.getElementById('filter-location');
const inputInclude = document.getElementById('filter-include');
const inputExclude = document.getElementById('filter-exclude');
const selectSort = document.getElementById('sort-type');

// Fetch Data
async function loadData() {
    try {
        container.innerHTML = `<div class="loading-state"><i class="ph ph-spinner ph-spin"></i><p>正在拉取最新数据...</p></div>`;
        const res = await fetch('../data.json');
        if (!res.ok) throw new Error("无法读取数据");
        const data = await res.json();
        state.jobs = data;
        applyFilters();
    } catch (err) {
        container.innerHTML = `<div class="loading-state" style="color:#ef4444;"><i class="ph ph-warning"></i><p>未找到数据！请确保已经在终端运行了 python main.py。</p></div>`;
        console.error(err);
    }
}

// Pipeline
function applyFilters() {
    let result = [...state.jobs];

    // 1. Location Filter
    const locVal = inputLocation.value.trim().toLowerCase();
    if (locVal) {
        result = result.filter(j => (j.location || '').toLowerCase().includes(locVal));
    }

    // 2. Tech Include
    const incVal = inputInclude.value.trim().toLowerCase();
    if (incVal) {
        const keywords = incVal.split(',').map(s => s.trim()).filter(Boolean);
        result = result.filter(j => {
            const rawText = JSON.stringify(j.tech_tags || []).toLowerCase() + ' ' + (j.requirements || '').toLowerCase();
            return keywords.every(kw => rawText.includes(kw));
        });
    }

    // 3. Tech Exclude
    const excVal = inputExclude.value.trim().toLowerCase();
    if (excVal) {
        const keywords = excVal.split(',').map(s => s.trim()).filter(Boolean);
        result = result.filter(j => {
            const rawText = JSON.stringify(j.tech_tags || []).toLowerCase() + ' ' + (j.title || '').toLowerCase() + ' ' + (j.requirements || '').toLowerCase();
            return !keywords.some(kw => rawText.includes(kw));
        });
    }

    // 4. Sort (Simplified)
    const sortType = selectSort.value;
    if (sortType === 'default') {
        // No additional sort, use crawl order
    } else if (sortType === 'alphabetical') {
        result.sort((a, b) => (a.company || '').localeCompare(b.company || ''));
    }

    state.filteredJobs = result;
    render();
}

// Render UI
function render() {
    statCount.textContent = state.filteredJobs.length;
    
    if (state.filteredJobs.length === 0) {
        container.innerHTML = `<div class="loading-state"><i class="ph ph-empty"></i><p>无匹配岗位</p></div>`;
        return;
    }

    const html = state.filteredJobs.map((job, idx) => {
        const tagsHtml = (job.tech_tags || []).slice(0, 4).map(t => `<span class="tech-tag">${t}</span>`).join('');
        
        return `
            <div class="job-card glass-panel" style="animation-delay: ${idx * 0.05}s">
                <div class="card-indicator"></div>
                <div class="job-header">
                    <h3 class="job-title">${job.title || '未知岗位'}</h3>
                    <div class="job-salary">${job.salary || '薪资面议'}</div>
                </div>
                
                <div class="job-meta">
                    <div class="meta-item"><i class="ph ph-buildings"></i> ${job.company || '未知公司'}</div>
                    <div class="meta-item"><i class="ph ph-map-pin"></i> ${job.location || '未知'}</div>
                    <div class="meta-item"><i class="ph ph-globe"></i> ${job.source || '未知平台'}</div>
                </div>

                <div class="tech-tags">${tagsHtml}</div>
                
                <p class="job-req">${job.requirements || '未提供具体要求'}</p>
                
                <div class="job-footer">
                    <div class="source-badge">
                        <i class="ph ph-link"></i> ${job.source}
                    </div>
                    <a href="${job.job_url || '#'}" target="_blank" class="apply-btn">
                        查看详情 <i class="ph ph-arrow-up-right"></i>
                    </a>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

// Event Listeners
[inputLocation, inputInclude, inputExclude, selectSort].forEach(el => {
    el.addEventListener('input', applyFilters);
    el.addEventListener('change', applyFilters);
});

refreshBtn.addEventListener('click', loadData);

// Startup
document.addEventListener('DOMContentLoaded', loadData);
