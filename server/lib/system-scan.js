// @ts-check
// system-scan.js — Probes the system for AI tools, skills, rules, configs, and opportunities.
// Returns data grouped by host app so the UI can render per-app cards.

const fs = require('fs');
const path = require('path');
const { HOMEDIR, DATA_DIR, SKILLS_DIR } = require('./config');
const { countSkillFiles, listSkillNames } = require('./skills');
const {
  HOSTS,
  RULE_FILE_NAMES,
  INSTRUCTION_FILE_NAMES,
  CONFIG_FILE_NAMES,
  OPPORTUNITY_FILES,
} = require('./system-scan-definitions');
const { probeIDEs, probeAIExtensions } = require('./system-scan-ides');

// ---- Helpers ----

async function getDriveRoots() {
  const drives = [];
  if (process.platform === 'win32') {
    const checks = [];
    for (let i = 65; i <= 90; i++) {
      const root = `${String.fromCharCode(i)}:\\`;
      checks.push(
        fs.promises.stat(root).then(
          (s) => (s.isDirectory() ? root : null),
          () => null,
        ),
      );
    }
    const results = await Promise.all(checks);
    for (const r of results) if (r) drives.push(r);
  }
  return drives;
}

/** @param {string} p */
async function isFile(p) {
  try {
    return (await fs.promises.stat(p)).isFile();
  } catch {
    return false;
  }
}
/** @param {string} p */
async function isDir(p) {
  try {
    return (await fs.promises.stat(p)).isDirectory();
  } catch {
    return false;
  }
}

/** @param {string} p */
async function readJsonSafe(p) {
  try {
    return JSON.parse(await fs.promises.readFile(p, 'utf8'));
  } catch {
    return null;
  }
}

// ---- Host-grouped scan ----

/** @typedef {{ path: string, label: string, count: number, names: { bareId: string, name: string, cat: string }[], internal?: boolean }} SkillEntry */
/** @typedef {{ path: string, label: string }} FileEntry */
/** @typedef {{ path: string, count: number, servers: string[] }} McpEntry */
/** @typedef {{ type: string, label: string, description: string }} OpportunityEntry */

/**
 * @param {{ id: string, label: string, icon: string }} hostDef
 * @param {string} homedir
 */
async function probeHostDir(hostDef, homedir) {
  const hostPath = path.join(homedir, hostDef.id);
  if (!(await isDir(hostPath))) return null;

  /** @type {SkillEntry[]} */
  const skills = [];
  /** @type {FileEntry[]} */
  const configs = [];
  /** @type {FileEntry[]} */
  const instructions = [];
  /** @type {FileEntry[]} */
  const rules = [];
  /** @type {McpEntry[]} */
  const mcpServers = [];
  /** @type {OpportunityEntry[]} */
  const opportunities = [];

  const result = {
    id: hostDef.id,
    label: hostDef.label,
    icon: hostDef.icon,
    path: hostPath,
    skills,
    configs,
    instructions,
    rules,
    mcpServers,
    opportunities,
  };

  // Skills: standard skill dirs
  const skillDir = path.join(hostPath, 'skills');
  if ((await isDir(skillDir)) && countSkillFiles(skillDir) > 0) {
    result.skills.push({
      path: skillDir,
      label: `${hostDef.label} skills`,
      count: countSkillFiles(skillDir),
      names: listSkillNames(skillDir),
    });
  }

  // Skills: Claude plugin marketplace
  if (hostDef.id === '.claude') {
    const pluginDir = path.join(hostPath, 'plugins', 'marketplaces', 'claude-plugins-official', 'plugins');
    const externalDir = path.join(
      hostPath,
      'plugins',
      'marketplaces',
      'claude-plugins-official',
      'external_plugins',
    );
    if (await isDir(pluginDir)) {
      const count = countSkillFiles(pluginDir);
      if (count > 0)
        result.skills.push({
          path: pluginDir,
          label: 'Claude Plugins (official)',
          count,
          names: listSkillNames(pluginDir),
        });
    }
    if (await isDir(externalDir)) {
      const count = countSkillFiles(externalDir);
      if (count > 0)
        result.skills.push({
          path: externalDir,
          label: 'Claude Plugins (external)',
          count,
          names: listSkillNames(externalDir),
        });
    }
  }

  // Configs
  const configChecks = CONFIG_FILE_NAMES.map(async (name) => {
    const p = path.join(hostPath, name);
    if (await isFile(p)) result.configs.push({ path: p, label: name });
  });
  // Special config locations
  if (hostDef.id === '.cursor') {
    configChecks.push(
      (async () => {
        const mcpPath = path.join(hostPath, 'mcp.json');
        if (await isFile(mcpPath)) {
          if (!result.configs.some((c) => c.path === mcpPath))
            result.configs.push({ path: mcpPath, label: 'mcp.json' });
        }
      })(),
    );
  }
  if (hostDef.id === '.claude') {
    configChecks.push(
      (async () => {
        const desktopConfig = path.join(
          process.env.APPDATA || path.join(HOMEDIR, 'AppData', 'Roaming'),
          'Claude',
          'claude_desktop_config.json',
        );
        if (await isFile(desktopConfig))
          result.configs.push({ path: desktopConfig, label: 'claude_desktop_config.json' });
      })(),
    );
  }
  // Kiro: steering.md and settings
  if (hostDef.id === '.kiro') {
    configChecks.push(
      (async () => {
        const steering = path.join(hostPath, 'steering', 'steering.md');
        if (await isFile(steering))
          result.instructions.push({ path: steering, label: 'steering/steering.md' });
      })(),
    );
    configChecks.push(
      (async () => {
        const settings = path.join(hostPath, 'settings', 'settings.json');
        if (await isFile(settings)) result.configs.push({ path: settings, label: 'settings.json' });
      })(),
    );
  }
  // Antigravity: settings and AI extensions
  if (hostDef.id === '.antigravity') {
    configChecks.push(
      (async () => {
        const agSettings = path.join(
          process.env.APPDATA || path.join(HOMEDIR, 'AppData', 'Roaming'),
          'Antigravity',
          'User',
          'settings.json',
        );
        if (await isFile(agSettings)) result.configs.push({ path: agSettings, label: 'settings.json' });
      })(),
    );
  }
  // Gemini: GEMINI.md and antigravity MCP config
  if (hostDef.id === '.gemini') {
    configChecks.push(
      (async () => {
        const agMcp = path.join(hostPath, 'antigravity', 'mcp_config.json');
        if (!(await isFile(agMcp))) return;
        const json = await readJsonSafe(agMcp);
        const servers = json?.mcpServers || json?.servers || {};
        const count = Object.keys(servers).length;
        if (count > 0) result.mcpServers.push({ path: agMcp, count, servers: Object.keys(servers) });
        else result.configs.push({ path: agMcp, label: 'antigravity/mcp_config.json' });
      })(),
    );
  }
  await Promise.all(configChecks);

  // Instructions
  const instrChecks = INSTRUCTION_FILE_NAMES.map(async (name) => {
    const p = path.join(hostPath, name);
    if (await isFile(p)) result.instructions.push({ path: p, label: name });
  });
  // Special instruction dirs
  if (hostDef.id === '.claude') {
    instrChecks.push(
      (async () => {
        const projectsDir = path.join(hostPath, 'projects');
        if (!(await isDir(projectsDir))) return;
        try {
          const projEntries = await fs.promises.readdir(projectsDir);
          const memChecks = projEntries.map(async (proj) => {
            const memDir = path.join(projectsDir, proj, 'memory');
            if (!(await isDir(memDir))) return;
            try {
              const files = await fs.promises.readdir(memDir);
              for (const f of files) {
                if (f.endsWith('.md'))
                  result.instructions.push({ path: path.join(memDir, f), label: `memory/${f}` });
              }
            } catch {
              /* ignore */
            }
          });
          await Promise.all(memChecks);
        } catch {
          /* ignore */
        }
      })(),
    );
  }
  await Promise.all(instrChecks);

  // Rules
  const ruleChecks = RULE_FILE_NAMES.map(async (name) => {
    const p = path.join(hostPath, name);
    if (await isFile(p)) result.rules.push({ path: p, label: name });
  });
  if (hostDef.id === '.codex') {
    ruleChecks.push(
      (async () => {
        const rulesDir = path.join(hostPath, 'rules');
        if (!(await isDir(rulesDir))) return;
        try {
          const files = await fs.promises.readdir(rulesDir);
          const fileChecks = files.map(async (f) => {
            const p = path.join(rulesDir, f);
            if (await isFile(p)) result.rules.push({ path: p, label: `rules/${f}` });
          });
          await Promise.all(fileChecks);
        } catch {
          /* ignore */
        }
      })(),
    );
  }
  await Promise.all(ruleChecks);

  // MCP servers from host config
  const mcpConfigs = [];
  if (hostDef.id === '.claude') {
    mcpConfigs.push(
      path.join(
        process.env.APPDATA || path.join(HOMEDIR, 'AppData', 'Roaming'),
        'Claude',
        'claude_desktop_config.json',
      ),
    );
  }
  if (hostDef.id === '.codex') mcpConfigs.push(path.join(hostPath, 'mcp.json'));
  if (hostDef.id === '.cursor') mcpConfigs.push(path.join(hostPath, 'mcp.json'));
  if (hostDef.id === '.windsurf') mcpConfigs.push(path.join(hostPath, 'mcp.json'));
  const mcpChecks = mcpConfigs.map(async (mcpPath) => {
    if (!(await isFile(mcpPath))) return;
    const json = await readJsonSafe(mcpPath);
    const servers = json?.mcpServers || json?.mcp_servers || {};
    const count = Object.keys(servers).length;
    if (count > 0) result.mcpServers.push({ path: mcpPath, count, servers: Object.keys(servers) });
  });
  await Promise.all(mcpChecks);

  // Opportunities (missing global config)
  const expected = OPPORTUNITY_FILES[/** @type {keyof typeof OPPORTUNITY_FILES} */ (hostDef.id)];
  if (expected) {
    const filePath = path.join(hostPath, expected);
    const homedirFile = path.join(homedir, expected);
    // If config doesn't exist inside host dir or at homedir root
    if (!(await isFile(filePath)) && !(await isFile(homedirFile))) {
      result.opportunities.push({
        type: 'missing-global-config',
        label: expected,
        description: `${hostDef.label} does not have a global ${expected} file. Context Engine can create one from your rules.`,
      });
    }
  }

  return result;
}

/** @param {Array<{id: string, label: string, path: string, exe: string}>} ideList */
async function probeIdegGroup(ideList) {
  if (!ideList.length) return null;
  const perIde = await probeAIExtensions();
  return {
    id: 'ides',
    label: 'IDEs',
    icon: 'vscode',
    items: ideList,
    extensions: perIde,
  };
}

// ---- Main scan ----

/**
 * @param {string[]} customPaths
 * @param {{ skipDrives?: boolean, skipHomedir?: boolean, skipWorkspaces?: boolean }} [opts]
 */
async function scanSystem(customPaths = [], opts = {}) {
  const { skipDrives = true, skipHomedir = false, skipWorkspaces = false } = opts;
  const workspaces = skipWorkspaces ? [] : await readWorkspaces();

  /** @type {any[]} */
  const hosts = [];
  const seenHosts = new Set();

  // Probe host dirs from homedir
  if (!skipHomedir) {
    const homedirResults = await Promise.all(HOSTS.map((h) => probeHostDir(h, HOMEDIR)));
    for (const data of homedirResults) {
      if (data && !seenHosts.has(data.path)) {
        seenHosts.add(data.path);
        hosts.push(data);
      }
    }
  }

  // Probe host dirs from drives
  if (!skipDrives) {
    const drives = await getDriveRoots();
    const driveResults = await Promise.all(
      drives.flatMap((drive) =>
        HOSTS.map(async (h) => {
          const p = path.join(drive, h.id);
          if (seenHosts.has(p)) return null;
          if (!(await isDir(p))) return null;
          const isWin = process.platform === 'win32';
          const homedirVersion = path.join(HOMEDIR, h.id);
          if (isWin && (await isDir(homedirVersion)) && seenHosts.has(homedirVersion)) return null;
          const data = await probeHostDir(h, drive);
          if (data) seenHosts.add(p);
          return data;
        }),
      ),
    );
    for (const data of driveResults) {
      if (data) hosts.push(data);
    }
  }

  // Probe IDEs
  const ideList = skipDrives && skipHomedir ? [] : await probeIDEs();

  // Custom paths: scan as additional skill sources
  for (const cp of customPaths) {
    if (!(await isDir(cp))) continue;
    const count = countSkillFiles(cp);
    if (count <= 0) continue;
    let realPath = cp;
    try {
      realPath = await fs.promises.realpath(cp);
    } catch {
      /* use unresolved */
    }
    const isWin = process.platform === 'win32';
    const internalReal = await (async () => {
      try {
        return await fs.promises.realpath(SKILLS_DIR);
      } catch {
        return SKILLS_DIR;
      }
    })();
    const internal = isWin
      ? realPath.toLowerCase().startsWith(internalReal.toLowerCase() + path.sep) ||
        realPath.toLowerCase() === internalReal.toLowerCase()
      : realPath.startsWith(internalReal + path.sep) || realPath === internalReal;

    // Check if this path falls inside an existing host dir
    let matched = false;
    for (const h of hosts) {
      const hPath = isWin ? h.path.toLowerCase() : h.path;
      const cPath = isWin ? cp.toLowerCase() : cp;
      if (cPath.startsWith(hPath + path.sep) || cPath === hPath) {
        // Add as skill under existing host
        h.skills.push({ path: cp, label: path.basename(cp), count, names: listSkillNames(cp), internal });
        matched = true;
        break;
      }
    }
    if (!matched) {
      // Create a standalone host entry for this custom path
      hosts.push({
        id: 'custom-' + path.basename(cp).replace(/[^a-z0-9]/gi, '-'),
        label: path.basename(cp),
        icon: 'folder',
        path: cp,
        skills: [{ path: cp, label: path.basename(cp), count, names: listSkillNames(cp), internal }],
        configs: [],
        instructions: [],
        rules: [],
        mcpServers: [],
        opportunities: [],
      });
    }
  }

  // Scan for standalone rule/instruction files in homedir root and workspaces
  if (!skipHomedir) {
    await scanStandaloneFiles(HOMEDIR, hosts);
  }
  if (!skipDrives) {
    const drives = await getDriveRoots();
    await Promise.all(drives.map((d) => scanStandaloneFiles(d, hosts)));
  }
  await Promise.all(workspaces.map((/** @type {string} */ ws) => scanStandaloneFiles(ws, hosts)));

  // Filter out hosts with nothing found (empty dirs)
  const populated = hosts.filter(
    (h) =>
      h.skills.length > 0 ||
      h.configs.length > 0 ||
      h.instructions.length > 0 ||
      h.rules.length > 0 ||
      h.mcpServers.length > 0 ||
      h.opportunities.length > 0,
  );

  // IDE group
  const ides = await probeIdegGroup(ideList);

  return {
    hosts: populated,
    ides: ides ? ides.items : [],
    ideExtensions: ides ? ides.extensions : [],
    workspaces,
  };
}

/** @param {string} dir @param {Array<any>} hosts */
async function scanStandaloneFiles(dir, hosts) {
  if (!(await isDir(dir))) return;
  // Check for rule/instruction files at the dir root that don't belong to a host dir
  for (const name of RULE_FILE_NAMES) {
    const p = path.join(dir, name);
    if (!(await isFile(p))) continue;
    // Skip if it's inside a host dir we already scanned
    if (hosts.some((h) => p.startsWith(h.path + path.sep) || p === h.path)) continue;
    // Attach to a "standalone" section
    let standalone = hosts.find((h) => h.id === 'standalone-rules');
    if (!standalone) {
      standalone = {
        id: 'standalone-rules',
        label: 'Standalone Files',
        icon: 'folder',
        path: '',
        skills: [],
        configs: [],
        instructions: [],
        rules: [],
        mcpServers: [],
        opportunities: [],
      };
      hosts.push(standalone);
    }
    if (!standalone.rules.some(/** @param {FileEntry} r */ (r) => r.path === p))
      standalone.rules.push({ path: p, label: name });
  }
  for (const name of INSTRUCTION_FILE_NAMES) {
    const p = path.join(dir, name);
    if (!(await isFile(p))) continue;
    if (hosts.some((h) => p.startsWith(h.path + path.sep) || p === h.path)) continue;
    let standalone = hosts.find((h) => h.id === 'standalone-rules');
    if (!standalone) {
      standalone = {
        id: 'standalone-rules',
        label: 'Standalone Files',
        icon: 'folder',
        path: '',
        skills: [],
        configs: [],
        instructions: [],
        rules: [],
        mcpServers: [],
        opportunities: [],
      };
      hosts.push(standalone);
    }
    if (!standalone.instructions.some(/** @param {FileEntry} i */ (i) => i.path === p))
      standalone.instructions.push({ path: p, label: name });
  }
}

// workspaces.json is created at runtime by the projects API; absence is expected on first run
async function readWorkspaces() {
  try {
    const raw = await fs.promises.readFile(path.join(DATA_DIR, 'workspaces.json'), 'utf8');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed?.workspaces)) {
      return parsed.workspaces
        .map((/** @type {any} */ w) => (typeof w === 'string' ? w : w?.path))
        .filter(Boolean);
    }
  } catch {
    /* none */
  }
  return [];
}

module.exports = { scanSystem };
