// onboarding-populate.js — Seeds memory entries and creates a handoff from onboarding scan results.
// Loaded after store.js, before onboarding.js.

function populateOnboardingMemory(scanResults) {
  if (!scanResults?.hosts?.length) return;
  const mem = MS.getData() || { version: '1.1', entries: [] };
  const skipContent = new Set((mem.entries || []).map((e) => (typeof e === 'string' ? e : e.content || '')));
  const pending = [];
  const hosts = scanResults.hosts.filter((h) => {
    const n =
      h.skills.length + h.configs.length + h.instructions.length + h.rules.length + h.mcpServers.length;
    return n > 0 || h.opportunities.length > 0;
  });
  if (hosts.length) {
    const summary = hosts
      .map((h) => {
        const p = [];
        if (h.skills.length)
          p.push(h.skills.reduce((n, s) => n + (s.count || (s.names || []).length), 0) + ' skills');
        if (h.instructions.length) p.push(h.instructions.length + ' instruction files');
        if (h.rules.length) p.push(h.rules.length + ' rule files');
        if (h.configs.length) p.push(h.configs.length + ' config files');
        if (h.mcpServers.length) p.push(h.mcpServers.reduce((n, m) => n + m.count, 0) + ' MCP servers');
        return h.label + ' (' + p.join(', ') + ')';
      })
      .join('; ');
    const c = 'AI tools on this machine: ' + summary + '.';
    if (!skipContent.has(c))
      pending.push({ id: 'entry_ob_' + Date.now(), category: 'workspace', label: '', content: c });
  }
  const ides = scanResults.ides || [];
  if (ides.length) {
    const c = 'IDEs installed: ' + ides.map((i) => i.label).join(', ') + '.';
    if (!skipContent.has(c))
      pending.push({ id: 'entry_ob_ide_' + Date.now(), category: 'workspace', label: '', content: c });
  }
  const exts = [...new Set(Object.values(scanResults.ideExtensions || {}).flat())];
  if (exts.length) {
    const c = 'AI extensions detected: ' + exts.join(', ') + '.';
    if (!skipContent.has(c))
      pending.push({ id: 'entry_ob_ext_' + Date.now(), category: 'workspace', label: '', content: c });
  }
  if (pending.length) {
    mem.entries = [...(mem.entries || []), ...pending];
    MS.save(mem);
  }
}

function populateOnboardingHandoff(scanResults) {
  if (!scanResults?.hosts?.length) return;
  const hosts = scanResults.hosts.filter((h) => {
    const n =
      h.skills.length + h.configs.length + h.instructions.length + h.rules.length + h.mcpServers.length;
    return n > 0 || h.opportunities.length > 0;
  });
  if (!hosts.length) return;
  const lines = ['# Onboarding Scan Results', '', '## AI Tools Detected'];
  for (const h of hosts) {
    lines.push('', '### ' + h.label, 'Path: ' + (h.path || 'N/A'));
    if (h.skills.length) {
      lines.push('', '**Skills:**');
      h.skills.forEach((sk) =>
        lines.push('- ' + sk.label + ' (' + (sk.count || (sk.names || []).length) + ')'),
      );
    }
    if (h.instructions.length) {
      lines.push('', '**Instructions:**');
      h.instructions.forEach((i) => lines.push('- ' + i.label + ' (' + i.path + ')'));
    }
    if (h.rules.length) {
      lines.push('', '**Rules:**');
      h.rules.forEach((r) => lines.push('- ' + r.label + ' (' + r.path + ')'));
    }
    if (h.configs.length) {
      lines.push('', '**Configs:**');
      h.configs.forEach((c) => lines.push('- ' + c.label + ' (' + c.path + ')'));
    }
    if (h.mcpServers.length) {
      lines.push('', '**MCP Servers:**');
      h.mcpServers.forEach((m) => lines.push('- ' + m.path + ' (' + m.count + ' servers)'));
    }
    if (h.opportunities.length) {
      lines.push('', '**Opportunities:**');
      h.opportunities.forEach((o) => lines.push('- ' + o.label + ': ' + o.description));
    }
  }
  if ((scanResults.ides || []).length) {
    lines.push('', '## IDEs');
    scanResults.ides.forEach((ide) => lines.push('- ' + ide.label + ' (' + ide.path + ')'));
  }
  const extByIde = scanResults.ideExtensions || {};
  if (Object.keys(extByIde).length) {
    lines.push('', '## AI Extensions');
    for (const [ide, exts] of Object.entries(extByIde)) lines.push('- ' + ide + ': ' + exts.join(', '));
  }
  return apiFetch('/handoffs', 'POST', {
    title: 'Onboarding Scan',
    body: lines.join('\n'),
    type: 'thread',
    thread_tag: 'onboarding-scan',
  }).catch(() => {});
}
