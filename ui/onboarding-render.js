// @ts-nocheck
// onboarding-render.js — Host and IDE card markup for the onboarding scan results.

const OnboardingRender = (() => {
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function hostIcon(iconId) {
    return obIcon(iconId);
  }

  function ideIconKey(label) {
    return window.ideIconKey ? window.ideIconKey(label) : 'vscode';
  }

  function renderHostCard(h, skillSources) {
    const srcByPath = {};
    for (const s of skillSources) {
      if (s.path && s.type !== 'internal') srcByPath[s.path.toLowerCase()] = s;
    }
    const totalForHost =
      h.skills.length + h.configs.length + h.instructions.length + h.rules.length + h.mcpServers.length;
    const sections = [];

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

  return { renderHostCard, renderIdeCard };
})();
