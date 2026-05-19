// @ts-nocheck
// onboarding.js — Full-window 3-step setup: scan → build → done.
// Results grouped by host app, with skills, rules, configs, and opportunities per app.

const Onboarding = (() => {
  const STEPS = [
    { num: 1, label: 'Scan' },
    { num: 2, label: 'Build' },
    { num: 3, label: 'Done' },
  ];

  let step = 1;
  let mounted = false;

  let scanResults = null;
  let scanning = false;
  let scanPhase = 'config';
  let customScanPaths = [];
  let scanConfig = { drives: true, homedir: true, workspaces: true };
  let indexing = false;
  let buildDone = false;
  let hosts = [];
  let skillSources = [];

  function root() {
    let el = document.getElementById('onboarding-root');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'onboarding-root';
    document.body.appendChild(el);
    return el;
  }

  async function init() {
    const summary = await DS.getOnboarding();
    if (!summary?.shouldShow) return false;
    mounted = true;
    step = 1;
    scanPhase = 'config';
    await loadData();
    render();
    return true;
  }

  async function loadData() {
    try {
      const [h, ss] = await Promise.all([DS.getMcpHosts(), DS.listSkillSources()]);
      hosts = h?.hosts || [];
      skillSources = ss?.sources || [];
      if (typeof loadSkillData === 'function') await loadSkillData();
    } catch {
      /* ignore */
    }
  }

  // ---- Step 1: Scan ----
  async function runScan() {
    scanPhase = 'scanning';
    scanning = true;
    scanResults = null;
    render();
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    advanceProgress(15, 'Probing drives...');
    try {
      const body = {
        customPaths: customScanPaths,
        skipDrives: !scanConfig.drives,
        skipHomedir: !scanConfig.homedir,
        skipWorkspaces: !scanConfig.workspaces,
      };
      advanceProgress(30, 'Scanning host applications...');
      const resp = await apiFetch('/system/scan', 'POST', body);
      scanResults = resp || {};
      advanceProgress(80, 'Linking discovered sources...');
      const candidates = collectSkillSources();
      for (let i = 0; i < candidates.length; i += 6) {
        const batch = candidates.slice(i, i + 6);
        await Promise.all(
          batch.map((c) => DS.addSkillSource({ path: c.path, label: c.label || c.path }).catch(() => {})),
        );
      }
      await loadData();
      advanceProgress(90, 'Populating memory and handoff...');
      populateOnboardingMemory(scanResults);
      await populateOnboardingHandoff(scanResults);
      advanceProgress(100, 'Complete');
    } catch {
      const [h, ss] = await Promise.all([DS.getMcpHosts(), DS.listSkillSources()]);
      scanResults = { hosts: [], ides: [], ideExtensions: [], workspaces: [] };
    } finally {
      advanceProgress(100, 'Complete');
      await new Promise((r) => setTimeout(r, 300));
      scanning = false;
      scanPhase = 'results';
      render();
    }
  }

  function collectSkillSources() {
    if (!scanResults?.hosts) return [];
    const sources = [];
    const seen = new Set();
    for (const host of scanResults.hosts) {
      for (const sk of host.skills || []) {
        if (sk.internal) continue;
        const key = sk.path.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        const alreadyLinked = skillSources.some((s) => s.path && s.path.toLowerCase() === key);
        if (!alreadyLinked) sources.push({ path: sk.path, label: sk.label || host.label + ' skills' });
      }
    }
    return sources;
  }

  function addScanPath(p) {
    if (!p || customScanPaths.includes(p)) return;
    customScanPaths.push(p);
    render();
  }

  function removeScanPath(idx) {
    customScanPaths.splice(idx, 1);
    render();
  }

  async function browseScanPath() {
    const picker = window.contextEngineDesktop?.selectFolder;
    if (!picker) return;
    try {
      const picked = await picker({ title: 'Pick a directory to scan' });
      if (picked) addScanPath(picked);
    } catch {
      /* ignore */
    }
  }

  async function linkPath(path, label) {
    const result = await DS.addSkillSource({ path, label: label || path });
    if (result?.ok) {
      Toast.success('Source linked');
      await loadData();
      render();
    } else {
      Toast.error(result?.error || 'Could not link source');
    }
  }

  async function unlinkSource(id) {
    const result = await DS.removeSkillSource(id);
    if (result?.ok) {
      Toast.success('Source unlinked');
      await loadData();
      render();
    } else {
      Toast.error(result?.error || 'Could not unlink source');
    }
  }

  async function buildIndex() {
    if (indexing) return;
    indexing = true;
    render();
    try {
      const result = await DS.indexSkills();
      buildDone = !!(result && result.ok !== false);
      if (buildDone) Toast.success('Vector index built');
      else
        Toast.error(
          'Ollama not available — ' +
            (result?.error || 'embedding failed') +
            '. You can skip indexing and continue.',
        );
    } catch {
      Toast.error('Index build failed — Ollama may not be running.');
    } finally {
      indexing = false;
      render();
    }
  }

  async function finish() {
    try {
      await DS.completeOnboarding();
    } catch {
      /* ignore */
    }
    Toast.success('Setup complete');
    close();
    if (typeof DashboardTab !== 'undefined') {
      try {
        await DashboardTab.init();
      } catch {
        /* ignore */
      }
    }
    if (typeof MemoryTab !== 'undefined') {
      try {
        await MS.loadFromServer();
        MemoryTab.init();
      } catch {
        /* ignore */
      }
    }
    if (typeof HandoffsTab !== 'undefined') {
      try {
        await HandoffsTab.load();
      } catch {
        /* ignore */
      }
    }
  }

  async function skip() {
    try {
      await DS.completeOnboarding();
    } catch {
      /* ignore */
    }
    close();
  }

  function close() {
    mounted = false;
    const el = document.getElementById('onboarding-root');
    if (el) el.remove();
  }

  function go(next) {
    step = next;
    render();
    window.scrollTo(0, 0);
  }

  // ---- Render ----
  function renderSteps() {
    return STEPS.map((s, idx) => {
      const state = s.num < step ? 'done' : s.num === step ? 'current' : '';
      const connector = idx < STEPS.length - 1 ? `<span class="ob-step-connector"></span>` : '';
      return `
        <div class="ob-step-pill ${state}">
          <span class="ob-step-num">${s.num}</span>
          <span class="ob-step-label">${s.label}</span>
        </div>
        ${connector}
      `;
    }).join('');
  }

  function render() {
    root().innerHTML = `
      <div class="ob-root">
        <div class="ob-drag"></div>
        <h1 class="ob-title">Onboarding</h1>
        <nav class="ob-steps">
          <div class="ob-steps-inner">${renderSteps()}</div>
        </nav>
        <main class="ob-body">
          <div class="ob-body-inner">
            ${step === 1 ? renderScan() : ''}
            ${step === 2 ? renderBuild() : ''}
            ${step === 3 ? renderDone() : ''}
          </div>
        </main>
      </div>
    `;
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  const ICONS = ObIcons;

  function hostIcon(iconId) {
    return obIcon(iconId);
  }

  // ---- Step 1: Scan ----
  function renderScan() {
    if (scanPhase === 'config') return renderScanConfig();
    if (scanPhase === 'scanning') return renderScanProgress();
    return renderScanResults();
  }

  function renderScanConfig() {
    const DEFAULT_LOCS = [
      {
        key: 'homedir',
        label: 'Home directory',
        desc: 'Your .claude, .codex, .cursor, .kimi, and other AI tool configs',
      },
      {
        key: 'drives',
        label: 'All fixed drives',
        desc: 'Scan E:\\, C:\\, and other drives for skills and configs',
      },
      {
        key: 'workspaces',
        label: 'Workspace directories',
        desc: 'Project folders registered with Context Engine',
      },
    ];
    return `
      <div class="ob-step-head">
        <h2>Where should we look?</h2>
        <p>Context Engine scans for AI tools, skill folders, rules, configs, and MCP servers on your machine.</p>
      </div>
      <div class="ob-section">
        <div class="ob-section-head">
          <span class="ob-section-label">Scan locations</span>
        </div>
        <div class="ob-row-list">
          ${DEFAULT_LOCS.map(
            (loc) => `
            <div class="ob-row${!scanConfig[loc.key] ? ' ob-row-dim' : ''}">
              <div class="ob-row-body">
                <span class="ob-row-name">${esc(loc.label)}</span>
                <span class="ob-row-desc">${esc(loc.desc)}</span>
              </div>
              <label class="toggle"><input type="checkbox" ${scanConfig[loc.key] ? 'checked' : ''} onchange="Onboarding.toggleLoc('${loc.key}', this.checked)" /><span class="toggle-track"></span></label>
            </div>
          `,
          ).join('')}
        </div>
      </div>
      <div class="ob-section">
        <div class="ob-section-head">
          <span class="ob-section-label">Custom paths</span>
        </div>
        ${
          customScanPaths.length
            ? `
          <div class="ob-row-list">
            ${customScanPaths
              .map(
                (p, i) => `
              <div class="ob-row">
                <div class="ob-row-body"><span class="ob-row-path">${esc(p)}</span></div>
                <button class="fb small" onclick="Onboarding.removeScanPath(${i})">Remove</button>
              </div>
            `,
              )
              .join('')}
          </div>
        `
            : '<div class="ob-empty">No custom paths added. Add a folder to scan for skills and configs.</div>'
        }
        ${
          typeof window !== 'undefined' && window.contextEngineDesktop?.selectFolder
            ? `
          <div class="ob-source-form">
            <button class="fb" type="button" onclick="Onboarding.browseScanPath()">+ Add directory</button>
          </div>
        `
            : ''
        }
      </div>
      <div class="ob-actions ob-mt-7">
        <button class="ob-skip" onclick="Onboarding.skip()">Skip setup</button>
        <button class="save-btn" onclick="Onboarding.runScan()">Start scan</button>
      </div>`;
  }

  function toggleLoc(key, on) {
    scanConfig[key] = on;
    render();
  }

  function renderScanProgress() {
    return `
      <div class="ob-scanning">
        <div class="ob-progress-track">
          <div class="ob-progress-fill" style="width:0%" id="ob-progress-fill"></div>
        </div>
        <div class="ob-scanning-text">
          <strong>Scanning your system</strong>
          <span id="ob-progress-label">Probing drives and standard paths...</span>
        </div>
      </div>`;
  }

  function advanceProgress(pct, label) {
    const fill = document.getElementById('ob-progress-fill');
    const lbl = document.getElementById('ob-progress-label');
    if (fill) fill.style.width = pct + '%';
    if (lbl) lbl.textContent = label || lbl.textContent;
  }

  function totalItems() {
    if (!scanResults?.hosts) return 0;
    let total = 0;
    for (const h of scanResults.hosts) {
      total +=
        h.skills.length + h.configs.length + h.instructions.length + h.rules.length + h.mcpServers.length;
    }
    total += Object.values(scanResults.ideExtensions || {}).reduce(
      (sum, exts) => sum + (Array.isArray(exts) ? exts.length : 0),
      0,
    );
    return total;
  }

  function renderScanResults() {
    const hostList = scanResults?.hosts || [];
    const ideList = scanResults?.ides || [];
    const extList = scanResults?.ideExtensions || [];
    if (!hostList.length && !ideList.length) {
      return `
        <div class="ob-step-head">
          <h2>No AI tools found</h2>
          <p>We could not detect any AI applications, skill folders, or config files. Add a custom path and try again.</p>
        </div>
        <div class="ob-actions ob-mt-7">
          <button class="ob-skip" onclick="Onboarding.skip()">Skip setup</button>
          <button class="fb" onclick="Onboarding.go(1)">Back</button>
        </div>`;
    }
    return `
      <div class="ob-step-head">
        <h2>What we found</h2>
        <p><strong>${totalItems()}</strong> items across <strong>${hostList.length}</strong> AI tool${hostList.length !== 1 ? 's' : ''}.</p>
      </div>
      <div class="ob-host-cards">
        ${hostList.map((h) => renderHostCard(h)).join('')}
        ${ideList.length ? renderIdeCard(ideList, extList) : ''}
      </div>
      <div class="ob-actions ob-mt-7">
        <button class="ob-skip" onclick="Onboarding.skip()">Skip setup</button>
        <button class="save-btn" onclick="Onboarding.go(2)">Continue to build</button>
      </div>`;
  }

  function renderHostCard(h) {
    const srcByPath = {};
    for (const s of skillSources) {
      if (s.path && s.type !== 'internal') srcByPath[s.path.toLowerCase()] = s;
    }
    const totalForHost =
      h.skills.length + h.configs.length + h.instructions.length + h.rules.length + h.mcpServers.length;
    const sections = [];

    // Skills
    if (h.skills.length) {
      sections.push(`
        <div class="ob-host-section">
          <button class="ob-host-section-hdr" onclick="this.parentElement.classList.toggle('ob-host-section-open')">
            ${catSvg('skills')}<span>Skills (${h.skills.map((s) => s.count || (s.names || []).length).reduce((a, b) => a + b, 0)})</span>
            <svg class="ob-accordion-chev" width="14" height="14" viewBox="0 0 14 14"><path d="M4 5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <div class="ob-host-section-body">
            ${h.skills
              .map((sk) => {
                const key = (sk.path || '').toLowerCase();
                const src = srcByPath[key];
                const escPath = esc(sk.path || '').replace(/\\/g, '\\\\');
                const escLabel = esc(sk.label || sk.path || '');
                const names = sk.names || [];
                const count = sk.count || names.length;
                return `
              <div class="ob-skill-source">
                <div class="ob-skill-source-hdr">
                  <span class="ob-row-name">${escLabel}</span>
                  <span class="ct-badge">${count} skill${count !== 1 ? 's' : ''}</span>
                </div>
                ${
                  names.length
                    ? `<ul class="ob-skill-list">${names
                        .slice(0, 20)
                        .map((n) => `<li><span class="ob-skill-cat">${esc(n.cat)}</span>${esc(n.name)}</li>`)
                        .join(
                          '',
                        )}${names.length > 20 ? `<li class="ob-muted">+${names.length - 20} more</li>` : ''}</ul>`
                    : ''
                }
                <div class="ob-host-actions">
                  ${sk.internal ? '<span class="ct-badge ok">Internal</span>' : src ? `<span class="ct-badge ok">Linked</span><button class="fb small" onclick="event.stopPropagation();Onboarding.unlinkSource('${esc(src.id)}')">Unlink</button>` : `<button class="fb small" onclick="event.stopPropagation();Onboarding.linkPath('${escPath}','${escLabel}')">Link</button>`}
                </div>
              </div>`;
              })
              .join('')}
          </div>
        </div>`);
    }

    // Instructions
    if (h.instructions.length) {
      sections.push(`
        <div class="ob-host-section">
          <button class="ob-host-section-hdr" onclick="this.parentElement.classList.toggle('ob-host-section-open')">
            ${catSvg('instruct')}<span>Instructions (${h.instructions.length})</span>
            <svg class="ob-accordion-chev" width="14" height="14" viewBox="0 0 14 14"><path d="M4 5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <div class="ob-host-section-body">
            <ul class="ob-file-list">${h.instructions.map((i) => `<li>${catSvg('instruct')}<span>${esc(i.label)}</span><span class="ob-file-path">${esc(i.path)}</span></li>`).join('')}</ul>
          </div>
        </div>`);
    }

    // Rules
    if (h.rules.length) {
      sections.push(`
        <div class="ob-host-section">
          <button class="ob-host-section-hdr" onclick="this.parentElement.classList.toggle('ob-host-section-open')">
            ${catSvg('rules')}<span>Rules (${h.rules.length})</span>
            <svg class="ob-accordion-chev" width="14" height="14" viewBox="0 0 14 14"><path d="M4 5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <div class="ob-host-section-body">
            <ul class="ob-file-list">${h.rules.map((r) => `<li>${catSvg('rules')}<span>${esc(r.label)}</span><span class="ob-file-path">${esc(r.path)}</span></li>`).join('')}</ul>
          </div>
        </div>`);
    }

    // Configs
    if (h.configs.length) {
      sections.push(`
        <div class="ob-host-section">
          <button class="ob-host-section-hdr" onclick="this.parentElement.classList.toggle('ob-host-section-open')">
            ${catSvg('config')}<span>Config (${h.configs.length})</span>
            <svg class="ob-accordion-chev" width="14" height="14" viewBox="0 0 14 14"><path d="M4 5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <div class="ob-host-section-body">
            <ul class="ob-file-list">${h.configs.map((c) => `<li>${catSvg('config')}<span>${esc(c.label)}</span><span class="ob-file-path">${esc(c.path)}</span></li>`).join('')}</ul>
          </div>
        </div>`);
    }

    // MCP
    if (h.mcpServers.length) {
      sections.push(`
        <div class="ob-host-section">
          <button class="ob-host-section-hdr" onclick="this.parentElement.classList.toggle('ob-host-section-open')">
            ${catSvg('mcp')}<span>MCP Servers (${h.mcpServers.reduce((a, m) => a + m.count, 0)})</span>
            <svg class="ob-accordion-chev" width="14" height="14" viewBox="0 0 14 14"><path d="M4 5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <div class="ob-host-section-body">
            ${h.mcpServers.map((m) => `<div class="ob-mcp-entry"><span class="ob-mcp-path">${esc(m.path)}</span><span class="ct-badge">${m.count} server${m.count !== 1 ? 's' : ''}</span>${m.servers ? `<ul class="ob-mcp-servers">${m.servers.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>` : ''}</div>`).join('')}
          </div>
        </div>`);
    }

    // Opportunities
    if (h.opportunities.length) {
      sections.push(`
        <div class="ob-host-section ob-host-opportunity">
          <button class="ob-host-section-hdr" onclick="this.parentElement.classList.toggle('ob-host-section-open')">
            ${catSvg('opportunity')}<span>Opportunities (${h.opportunities.length})</span>
            <svg class="ob-accordion-chev" width="14" height="14" viewBox="0 0 14 14"><path d="M4 5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <div class="ob-host-section-body">
            ${h.opportunities
              .map(
                (o) => `
              <div class="ob-opportunity">
                <span class="ob-opportunity-label">${esc(o.label)}</span>
                <span class="ob-opportunity-desc">${esc(o.description)}</span>
              </div>
            `,
              )
              .join('')}
          </div>
        </div>`);
    }

    return `
      <div class="ob-host-card">
        <div class="ob-host-card-hdr">
          <div class="ob-row-icon">${hostIcon(h.icon || h.id)}</div>
          <div class="ob-host-card-info">
            <span class="ob-row-name">${esc(h.label)}</span>
            ${h.path ? `<span class="ob-row-path">${esc(h.path)}</span>` : ''}
          </div>
          <span class="ct-badge">${totalForHost} item${totalForHost !== 1 ? 's' : ''}</span>
        </div>
        ${sections.join('')}
      </div>`;
  }

  function ideIconKey(label) {
    return window.ideIconKey ? window.ideIconKey(label) : 'vscode';
  }

  function renderIdeCard(ideList, extByIde) {
    return `
      <div class="ob-host-card">
        <div class="ob-host-card-hdr">
          <div class="ob-row-icon">${hostIcon('vscode')}</div>
          <div class="ob-host-card-info">
            <span class="ob-row-name">IDEs</span>
            <span class="ob-row-path">${ideList.map((ide) => esc(ide.label)).join(', ')}</span>
          </div>
          <span class="ct-badge">${ideList.length} IDE${ideList.length !== 1 ? 's' : ''}</span>
        </div>
        <div class="ob-host-section ob-host-section-open">
          <div class="ob-host-section-body">
            ${ideList
              .map(
                (ide) => `
              <div class="ob-ide-ext-row">
                <div class="ob-ide-ext-label-group">
                  <div class="ob-row-icon ob-row-icon-sm">${hostIcon(ideIconKey(ide.label))}</div>
                  <span class="ob-ide-ext-label">${esc(ide.label)}</span>
                </div>
                <div class="ob-ext-badges">${extByIde && extByIde[ide.label] ? extByIde[ide.label].map((e) => `<span class="ct-badge">${esc(e)}</span>`).join('') : ''}</div>
              </div>
            `,
              )
              .join('')}
          </div>
        </div>
      </div>`;
  }

  // ---- Step 2: Build ----
  function renderBuild() {
    const srcCount = skillSources.length;
    const skillCount = Array.isArray(SKILL_DATA) ? SKILL_DATA.length : 0;
    if (buildDone) {
      return `
        <div class="ob-moment">
          <div class="ob-moment-badge done">&#10003;</div>
          <div class="ob-moment-text">
            <strong>Index built</strong>
            <span>${skillCount} skills from ${srcCount} source${srcCount !== 1 ? 's' : ''} indexed. Your AI hosts can now retrieve relevant context through Context Engine.</span>
          </div>
          <div class="ob-actions">
            <button class="save-btn" onclick="Onboarding.go(3)">Continue</button>
          </div>
        </div>`;
    }
    if (indexing) {
      return `
        <div class="ob-moment">
          <div class="ob-moment-badge spin"></div>
          <div class="ob-moment-text">
            <strong>Building vector index</strong>
            <span>Embedding ${skillCount} skills from ${srcCount} source${srcCount !== 1 ? 's' : ''} via Ollama. This usually takes 10-60 seconds.</span>
          </div>
        </div>`;
    }
    return `
      <div class="ob-step-head">
        <h2>Build vector index</h2>
        <p>Context Engine indexes your ${skillCount} skills from ${srcCount} source${srcCount !== 1 ? 's' : ''} so host apps can retrieve relevant context instantly through semantic search.</p>
        <span class="ob-step-total">${skillCount} skills to index</span>
      </div>
      <div class="ob-actions ob-mt-7">
        <button class="ob-skip" onclick="Onboarding.skip()">Skip setup</button>
        <button class="fb" onclick="Onboarding.go(1)">Back</button>
        <button class="save-btn" onclick="Onboarding.buildIndex()">Build index</button>
        <button class="fb small" onclick="Onboarding.go(3)" style="margin-left:auto">Skip to done</button>
      </div>`;
  }

  // ---- Step 3: Done ----
  function renderDone() {
    const hostList = scanResults?.hosts || [];
    const opportunities = hostList.flatMap((h) => h.opportunities.map((o) => ({ ...o, host: h.label })));
    const totalSkills = Array.isArray(SKILL_DATA) ? SKILL_DATA.length : 0;
    const srcCount = skillSources.length;
    const memEntries = (MS.getData()?.entries || []).length;
    return `
      <div class="ob-moment">
        <div class="ob-moment-badge done">&#10003;</div>
        <div class="ob-moment-text">
          <strong>All set</strong>
          <span>${totalSkills} skills indexed from ${srcCount} source${srcCount !== 1 ? 's' : ''}. ${memEntries} memory entries loaded. AI hosts can retrieve context through MCP or compiled files.</span>
        </div>
      </div>
      ${
        opportunities.length
          ? `
        <div class="ob-section ob-mt-7">
          <div class="ob-section-head">
            <span class="ob-section-label">Push your rules to apps that need them</span>
          </div>
          <div class="ob-row-list">
            ${opportunities
              .map(
                (o) => `
              <div class="ob-row ob-row-opportunity">
                <div class="ob-row-icon">${catSvg('opportunity')}</div>
                <div class="ob-row-body">
                  <span class="ob-row-name">${esc(o.host)}: ${esc(o.label)}</span>
                  <span class="ob-row-desc">${esc(o.description)}</span>
                </div>
              </div>
            `,
              )
              .join('')}
          </div>
        </div>
      `
          : ''
      }
      <div class="ob-actions ob-mt-7">
        <button class="save-btn" onclick="Onboarding.finish()">Go to dashboard</button>
      </div>`;
  }

  return {
    init,
    go,
    runScan,
    linkPath,
    unlinkSource,
    buildIndex,
    finish,
    skip,
    addScanPath,
    removeScanPath,
    browseScanPath,
    toggleLoc,
  };
})();
