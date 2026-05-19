// @ts-check
// system-scan-ides.js — Installed IDE and AI extension probes.

const fs = require('fs');
const path = require('path');
const { HOMEDIR } = require('./config');
const { IDE_PROBE_PATHS, AI_EXTENSION_PATTERNS } = require('./system-scan-definitions');

/** @param {string} env */
function expandEnvVar(env) {
  return env.replace(
    /%([^%]+)%/g,
    (_ /** @type {string} */, v /** @type {string} */) => process.env[v] || '',
  );
}

/** @param {string} p */
async function isDir(p) {
  try {
    return (await fs.promises.stat(p)).isDirectory();
  } catch {
    return false;
  }
}

async function probeIDEs() {
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
          if (await isDir(parentDir)) {
            const entries = await fs.promises.readdir(parentDir);
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
          if (await isDir(base)) resolvedPath = base;
        } catch {
          /* ignore */
        }
      }
      if (!resolvedPath) continue;
      const exePath = path.join(resolvedPath, ide.exe);
      try {
        const s = await fs.promises.stat(exePath);
        if (s.isFile()) {
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

async function probeAIExtensions() {
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
  const checks = ideExtDirs.map(async (ide) => {
    if (!(await isDir(ide.path))) return;
    try {
      const entries = await fs.promises.readdir(ide.path);
      const found = [];
      for (const ai of AI_EXTENSION_PATTERNS) {
        if (entries.some((e) => e.startsWith(ai.pattern))) found.push(ai.label);
      }
      if (found.length > 0) perIde[ide.label] = [...new Set(found)];
    } catch {
      /* ignore */
    }
  });
  await Promise.all(checks);
  return perIde;
}

module.exports = { probeIDEs, probeAIExtensions };
