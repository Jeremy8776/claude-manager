// @ts-check
// system-scan.js — Probes the system for AI tools, skills, rules, configs, and opportunities.
// Returns data grouped by host app so the UI can render per-app cards.

const fs = require('fs');
const path = require('path');
const { HOMEDIR, DATA_DIR, SKILLS_DIR } = require('./config');
const { countSkillFiles, listSkillNames } = require('./skills');

// ---- Host definitions ----

const HOSTS = [
  { id: '.claude', label: 'Claude Code', icon: 'claude' },
  { id: '.cursor', label: 'Cursor', icon: 'cursor' },
  { id: '.windsurf', label: 'Windsurf', icon: 'windsurf' },
  { id: '.codex', label: 'Codex CLI', icon: 'openai' },
  { id: '.opencode', label: 'OpenCode', icon: 'opencode' },
  { id: '.continue', label: 'Continue', icon: 'continue' },
  { id: '.roo', label: 'Roo CLI', icon: 'cline' },
  { id: '.cline', label: 'Cline', icon: 'cline' },
  { id: '.kimi', label: 'Kimi K2', icon: 'kimi' },
  { id: '.goose', label: 'Goose', icon: 'goose' },
  { id: '.amp', label: 'Amp', icon: 'sourcegraph' },
  { id: '.kiro', label: 'Kiro', icon: 'kiro' },
  { id: '.antigravity', label: 'Antigravity', icon: 'antigravity' },
  { id: '.gemini', label: 'Gemini', icon: 'gemini' },
  { id: '.augment', label: 'Augment', icon: 'augment' },
  { id: '.pearai', label: 'PearAI', icon: 'pearai' },
  { id: '.void', label: 'Void', icon: 'void' },
];

const RULE_FILE_NAMES = [
  '.clinerules',
  '.cursorrules',
  '.windsurfrules',
  '.rules',
  '.ampcoderc',
  '.goosehints',
];

const INSTRUCTION_FILE_NAMES = [
  'AGENTS.md',
  'CLAUDE.md',
  'GEMINI.md',
  'devin.md',
  'CONVENTIONS.md',
  '.kimi-system-prompt.md',
  '.github/copilot-instructions.md',
  'CONTEXT.md',
  'steering.md',
];

const CONFIG_FILE_NAMES = [
  'settings.json',
  'config.json',
  'config.toml',
  'kimi.json',
  'mcp.json',
  'claude_desktop_config.json',
];

const OPPORTUNITY_FILES = {
  '.claude': 'CLAUDE.md',
  '.cursor': '.cursorrules',
  '.windsurf': '.windsurfrules',
  '.codex': 'instructions.md',
  '.opencode': null,
  '.continue': null,
  '.roo': null,
  '.cline': '.clinerules',
  '.kimi': '.kimi-system-prompt.md',
  '.goose': '.goosehints',
  '.amp': '.ampcoderc',
  '.kiro': '.kiro/steering.md',
  '.antigravity': null,
  '.gemini': 'GEMINI.md',
  '.augment': '.augment-guidelines',
  '.pearai': '.pearai',
  '.void': null,
};

const IDE_PROBE_PATHS = [
  {
    exe: 'Code.exe',
    label: 'VS Code',
    dirs: [
      '%LOCALAPPDATA%\\Programs\\Microsoft VS Code',
      '%ProgramFiles%\\Microsoft VS Code',
      '%ProgramFiles(x86)%\\Microsoft VS Code',
    ],
  },
  {
    exe: 'Cursor.exe',
    label: 'Cursor',
    dirs: ['%LOCALAPPDATA%\\Programs\\cursor', '%ProgramFiles%\\Cursor'],
  },
  {
    exe: 'Windsurf.exe',
    label: 'Windsurf',
    dirs: ['%LOCALAPPDATA%\\Programs\\windsurf', '%ProgramFiles%\\Windsurf'],
  },
  { exe: 'Kiro.exe', label: 'Kiro', dirs: ['%LOCALAPPDATA%\\Programs\\Kiro'] },
  {
    exe: 'Antigravity.exe',
    label: 'Antigravity',
    dirs: ['%LOCALAPPDATA%\\Programs\\Antigravity', '%ProgramFiles%\\Antigravity'],
  },
  {
    exe: 'idea64.exe',
    label: 'IntelliJ IDEA',
    dirs: ['%ProgramFiles%\\JetBrains\\IntelliJ IDEA*', '%LOCALAPPDATA%\\JetBrains\\IntelliJ IDEA*'],
  },
  {
    exe: 'pycharm64.exe',
    label: 'PyCharm',
    dirs: ['%ProgramFiles%\\JetBrains\\PyCharm*', '%LOCALAPPDATA%\\JetBrains\\PyCharm*'],
  },
  {
    exe: 'webstorm64.exe',
    label: 'WebStorm',
    dirs: ['%ProgramFiles%\\JetBrains\\WebStorm*', '%LOCALAPPDATA%\\JetBrains\\WebStorm*'],
  },
  {
    exe: 'rider64.exe',
    label: 'Rider',
    dirs: ['%ProgramFiles%\\JetBrains\\Rider*', '%LOCALAPPDATA%\\JetBrains\\Rider*'],
  },
  {
    exe: 'goland64.exe',
    label: 'GoLand',
    dirs: ['%ProgramFiles%\\JetBrains\\GoLand*', '%LOCALAPPDATA%\\JetBrains\\GoLand*'],
  },
  {
    exe: 'clion64.exe',
    label: 'CLion',
    dirs: ['%ProgramFiles%\\JetBrains\\CLion*', '%LOCALAPPDATA%\\JetBrains\\CLion*'],
  },
  { exe: 'fleet.exe', label: 'JetBrains Fleet', dirs: ['%LOCALAPPDATA%\\Programs\\Fleet'] },
  { exe: 'sublime_text.exe', label: 'Sublime Text', dirs: ['%ProgramFiles%\\Sublime Text*'] },
  {
    exe: 'notepad++.exe',
    label: 'Notepad++',
    dirs: ['%ProgramFiles%\\Notepad++', '%ProgramFiles(x86)%\\Notepad++'],
  },
  {
    exe: 'devenv.exe',
    label: 'Visual Studio',
    dirs: ['%ProgramFiles%\\Microsoft Visual Studio*', '%ProgramFiles(x86)%\\Microsoft Visual Studio*'],
  },
  { exe: 'zed.exe', label: 'Zed', dirs: ['%LOCALAPPDATA%\\Programs\\Zed', '%ProgramFiles%\\Zed'] },
  { exe: 'Trae.exe', label: 'Trae', dirs: ['%LOCALAPPDATA%\\Programs\\Trae', '%ProgramFiles%\\Trae'] },
  {
    exe: 'PearAI.exe',
    label: 'PearAI',
    dirs: ['%LOCALAPPDATA%\\Programs\\PearAI', '%ProgramFiles%\\PearAI'],
  },
];

const AI_EXTENSION_PATTERNS = [
  { pattern: 'github.copilot', label: 'GitHub Copilot' },
  { pattern: 'github.copilot-chat', label: 'GitHub Copilot Chat' },
  { pattern: 'openai.chatgpt', label: 'ChatGPT' },
  { pattern: 'continue', label: 'Continue' },
  { pattern: 'cline', label: 'Cline' },
  { pattern: 'roo-code', label: 'Roo Code' },
  { pattern: 'aider', label: 'Aider' },
  { pattern: 'codeium', label: 'Codeium' },
  { pattern: 'tabnine', label: 'Tabnine' },
  { pattern: 'supermaven', label: 'Supermaven' },
  { pattern: 'amazonwebservices.aws-toolkit', label: 'AWS Q' },
  { pattern: 'sourcegraph.cody', label: 'Cody (Sourcegraph)' },
];

// ---- Helpers ----

function getDriveRoots() {
  const drives = [];
  if (process.platform === 'win32') {
    for (let i = 65; i <= 90; i++) {
      const root = `${String.fromCharCode(i)}:\\`;
      try {
        if (fs.statSync(root).isDirectory()) drives.push(root);
      } catch {
        /* skip */
      }
    }
  }
  return drives;
}

/** @param {string} env */
function expandEnvVar(env) {
  return env.replace(
    /%([^%]+)%/g,
    (_ /** @type {string} */, v /** @type {string} */) => process.env[v] || '',
  );
}

/** @param {string} p */
function isFile(p) {
  try {
    return fs.statSync(p).isFile();
  } catch {
    return false;
  }
}
/** @param {string} p */
function isDir(p) {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

/** @param {string} p */
function readJsonSafe(p) {
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch {
    return null;
  }
}

// ---- Probe functions ----

function probeIDEs() {
  const found = [];
  const seen = new Set();
  for (const ide of IDE_PROBE_PATHS) {
    if (seen.has(ide.label)) continue;
    let resolvedPath = null;
    for (const dirPattern of ide.dirs) {
      const base = expandEnvVar(dirPattern);
      if (!base) continue;
      if (base.includes('*')) {
        const wildIdx = base.indexOf('*');
        const prefix = base.substring(0, wildIdx);
        const parentDir = path.dirname(prefix);
        try {
          if (fs.statSync(parentDir).isDirectory()) {
            const entries = fs.readdirSync(parentDir);
            const match = entries
              .filter((e) => e.startsWith(path.basename(prefix)))
              .sort()
              .pop();
            if (match) resolvedPath = path.join(parentDir, match);
          }
        } catch {
          /* ignore */
        }
      }
      if (!resolvedPath) {
        try {
          if (fs.statSync(base).isDirectory()) resolvedPath = base;
        } catch {
          /* ignore */
        }
      }
      if (!resolvedPath) continue;
      const exePath = path.join(resolvedPath, ide.exe);
      try {
        if (fs.statSync(exePath).isFile()) {
          found.push({
            id: 'ide-' + ide.label.replace(/\s+/g, '-').toLowerCase(),
            label: ide.label,
            path: resolvedPath,
            exe: exePath,
          });
          seen.add(ide.label);
          break;
        }
      } catch {
        /* ignore */
      }
    }
  }
  return found;
}

function probeAIExtensions() {
  // Map: IDE label → Set of AI extension labels found in that IDE's extensions dir
  const ideExtDirs = [
    { label: 'VS Code', path: path.join(HOMEDIR, '.vscode', 'extensions') },
    {
      label: 'Cursor',
      path: path.join(
        process.env.APPDATA || path.join(HOMEDIR, 'AppData', 'Roaming'),
        'Cursor',
        'extensions',
      ),
    },
    { label: 'Kiro', path: path.join(HOMEDIR, '.kiro', 'extensions') },
    { label: 'Antigravity', path: path.join(HOMEDIR, '.antigravity', 'extensions') },
    { label: 'Trae', path: path.join(HOMEDIR, '.trae', 'extensions') },
    { label: 'PearAI', path: path.join(HOMEDIR, '.pearai', 'extensions') },
  ];
  /** @type {Record<string, string[]>} */
  const perIde = {};
  for (const ide of ideExtDirs) {
    if (!isDir(ide.path)) continue;
    try {
      const entries = fs.readdirSync(ide.path);
      const found = [];
      for (const ai of AI_EXTENSION_PATTERNS) {
        if (entries.some((e) => e.startsWith(ai.pattern))) found.push(ai.label);
      }
      if (found.length > 0) perIde[ide.label] = [...new Set(found)];
    } catch {
      /* ignore */
    }
  }
  return perIde;
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
function probeHostDir(hostDef, homedir) {
  const hostPath = path.join(homedir, hostDef.id);
  if (!isDir(hostPath)) return null;

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
  if (isDir(skillDir) && countSkillFiles(skillDir) > 0) {
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
    if (isDir(pluginDir)) {
      const count = countSkillFiles(pluginDir);
      if (count > 0)
        result.skills.push({
          path: pluginDir,
          label: 'Claude Plugins (official)',
          count,
          names: listSkillNames(pluginDir),
        });
    }
    if (isDir(externalDir)) {
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
  for (const name of CONFIG_FILE_NAMES) {
    const p = path.join(hostPath, name);
    if (isFile(p)) result.configs.push({ path: p, label: name });
  }
  // Special config locations
  if (hostDef.id === '.cursor') {
    const mcpPath = path.join(hostPath, 'mcp.json');
    if (isFile(mcpPath) && !result.configs.some((c) => c.path === mcpPath))
      result.configs.push({ path: mcpPath, label: 'mcp.json' });
  }
  if (hostDef.id === '.claude') {
    const desktopConfig = path.join(
      process.env.APPDATA || path.join(HOMEDIR, 'AppData', 'Roaming'),
      'Claude',
      'claude_desktop_config.json',
    );
    if (isFile(desktopConfig))
      result.configs.push({ path: desktopConfig, label: 'claude_desktop_config.json' });
  }
  // Kiro: steering.md and settings
  if (hostDef.id === '.kiro') {
    const steering = path.join(hostPath, 'steering', 'steering.md');
    if (isFile(steering)) result.instructions.push({ path: steering, label: 'steering/steering.md' });
    const settings = path.join(hostPath, 'settings', 'settings.json');
    if (isFile(settings)) result.configs.push({ path: settings, label: 'settings.json' });
  }
  // Antigravity: settings and AI extensions
  if (hostDef.id === '.antigravity') {
    const agSettings = path.join(
      process.env.APPDATA || path.join(HOMEDIR, 'AppData', 'Roaming'),
      'Antigravity',
      'User',
      'settings.json',
    );
    if (isFile(agSettings)) result.configs.push({ path: agSettings, label: 'settings.json' });
  }
  // Gemini: GEMINI.md and antigravity MCP config
  if (hostDef.id === '.gemini') {
    const agMcp = path.join(hostPath, 'antigravity', 'mcp_config.json');
    if (isFile(agMcp)) {
      const json = readJsonSafe(agMcp);
      const servers = json?.mcpServers || json?.servers || {};
      const count = Object.keys(servers).length;
      if (count > 0) result.mcpServers.push({ path: agMcp, count, servers: Object.keys(servers) });
      else result.configs.push({ path: agMcp, label: 'antigravity/mcp_config.json' });
    }
  }

  // Instructions
  for (const name of INSTRUCTION_FILE_NAMES) {
    const p = path.join(hostPath, name);
    if (isFile(p)) result.instructions.push({ path: p, label: name });
  }
  // Special instruction dirs
  if (hostDef.id === '.claude') {
    const projectsDir = path.join(hostPath, 'projects');
    if (isDir(projectsDir)) {
      try {
        for (const proj of fs.readdirSync(projectsDir)) {
          const memDir = path.join(projectsDir, proj, 'memory');
          if (isDir(memDir)) {
            try {
              for (const f of fs.readdirSync(memDir)) {
                if (f.endsWith('.md'))
                  result.instructions.push({ path: path.join(memDir, f), label: `memory/${f}` });
              }
            } catch {
              /* ignore */
            }
          }
        }
      } catch {
        /* ignore */
      }
    }
  }

  // Rules
  for (const name of RULE_FILE_NAMES) {
    const p = path.join(hostPath, name);
    if (isFile(p)) result.rules.push({ path: p, label: name });
  }
  if (hostDef.id === '.codex') {
    const rulesDir = path.join(hostPath, 'rules');
    if (isDir(rulesDir)) {
      try {
        for (const f of fs.readdirSync(rulesDir)) {
          const p = path.join(rulesDir, f);
          if (isFile(p)) result.rules.push({ path: p, label: `rules/${f}` });
        }
      } catch {
        /* ignore */
      }
    }
  }

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
  for (const mcpPath of mcpConfigs) {
    if (!isFile(mcpPath)) continue;
    const json = readJsonSafe(mcpPath);
    const servers = json?.mcpServers || json?.mcp_servers || {};
    const count = Object.keys(servers).length;
    if (count > 0) result.mcpServers.push({ path: mcpPath, count, servers: Object.keys(servers) });
  }

  // Opportunities (missing global config)
  const expected = OPPORTUNITY_FILES[/** @type {keyof typeof OPPORTUNITY_FILES} */ (hostDef.id)];
  if (expected) {
    const filePath = path.join(hostPath, expected);
    const homedirFile = path.join(homedir, expected);
    // If config doesn't exist inside host dir or at homedir root
    if (!isFile(filePath) && !isFile(homedirFile)) {
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
function probeIdegGroup(ideList) {
  if (!ideList.length) return null;
  const perIde = probeAIExtensions();
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
function scanSystem(customPaths = [], opts = {}) {
  const { skipDrives = false, skipHomedir = false, skipWorkspaces = false } = opts;
  const workspaces = skipWorkspaces ? [] : readWorkspaces();

  const hosts = [];
  const seenHosts = new Set();

  // Probe host dirs from homedir
  if (!skipHomedir) {
    for (const h of HOSTS) {
      const data = probeHostDir(h, HOMEDIR);
      if (data && !seenHosts.has(data.path)) {
        seenHosts.add(data.path);
        hosts.push(data);
      }
    }
  }

  // Probe host dirs from drives
  if (!skipDrives) {
    for (const drive of getDriveRoots()) {
      for (const h of HOSTS) {
        const p = path.join(drive, h.id);
        if (seenHosts.has(p)) continue;
        if (isDir(p)) {
          const isWin = process.platform === 'win32';
          // On Windows, drive-level host dirs overlap with homedir (same user)
          // Skip if we already found this host from homedir
          const homedirVersion = path.join(HOMEDIR, h.id);
          if (isWin && isDir(homedirVersion) && seenHosts.has(homedirVersion)) continue;
          const data = probeHostDir(h, drive);
          if (data) {
            seenHosts.add(p);
            hosts.push(data);
          }
        }
      }
    }
  }

  // Probe IDEs
  const ideList = skipDrives && skipHomedir ? [] : probeIDEs();

  // Custom paths: scan as additional skill sources
  for (const cp of customPaths) {
    if (!isDir(cp)) continue;
    const count = countSkillFiles(cp);
    if (count <= 0) continue;
    let realPath = cp;
    try {
      realPath = fs.realpathSync(cp);
    } catch {
      /* use unresolved */
    }
    const isWin = process.platform === 'win32';
    const internalReal = (() => {
      try {
        return fs.realpathSync(SKILLS_DIR);
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
    scanStandaloneFiles(HOMEDIR, hosts);
  }
  if (!skipDrives) {
    for (const drive of getDriveRoots()) scanStandaloneFiles(drive, hosts);
  }
  for (const ws of workspaces) scanStandaloneFiles(ws, hosts);

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
  const ides = probeIdegGroup(ideList);

  return {
    hosts: populated,
    ides: ides ? ides.items : [],
    ideExtensions: ides ? ides.extensions : [],
    workspaces,
  };
}

/** @param {string} dir @param {Array<any>} hosts */
function scanStandaloneFiles(dir, hosts) {
  if (!isDir(dir)) return;
  // Check for rule/instruction files at the dir root that don't belong to a host dir
  for (const name of RULE_FILE_NAMES) {
    const p = path.join(dir, name);
    if (!isFile(p)) continue;
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
    if (!isFile(p)) continue;
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

function readWorkspaces() {
  try {
    const raw = fs.readFileSync(path.join(DATA_DIR, 'workspaces.json'), 'utf8');
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
