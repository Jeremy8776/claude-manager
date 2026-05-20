// icons.js — Shared icon map and helpers for onboarding skill/IDE cards.

window.ObIcons = {
  claude: 'https://cdn.jsdelivr.net/npm/simple-icons/icons/claude.svg',
  cursor: 'https://cdn.jsdelivr.net/npm/simple-icons/icons/cursor.svg',
  windsurf: 'https://cdn.jsdelivr.net/npm/simple-icons/icons/windsurf.svg',
  openai: 'https://cdn.jsdelivr.net/npm/simple-icons/icons/openai.svg',
  opencode: 'https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/svg/opencode.svg',
  continue:
    'https://raw.githubusercontent.com/continuedev/continue/main/extensions/vscode/media/sidebar-icon.png',
  cline: 'https://cdn.jsdelivr.net/npm/simple-icons/icons/cline.svg',
  kimi: 'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/kimi-ai.svg',
  goose: 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/goose.svg',
  sourcegraph: 'https://upload.wikimedia.org/wikipedia/commons/8/8f/Sourcegraph-logo-light.svg',
  kiro: 'https://kiro.dev/favicon.ico',
  antigravity: 'https://avatars.githubusercontent.com/nicholasgriffintn?size=128',
  gemini: 'https://cdn.jsdelivr.net/npm/simple-icons/icons/googlegemini.svg',
  augment: 'https://www.augmentcode.com/favicon.svg',
  pearai: 'https://avatars.githubusercontent.com/nicepkg?size=128',
  void: 'https://avatars.githubusercontent.com/voideditor?size=128',
  vscode: 'https://cdn.jsdelivr.net/npm/simple-icons/icons/visualstudiocode.svg',
  folder: '',
  'ide-vs-code': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/visualstudiocode.svg',
  'ide-cursor': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/cursor.svg',
  'ide-windsurf': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/windsurf.svg',
  'ide-kiro': 'https://kiro.dev/favicon.ico',
  'ide-antigravity': 'https://avatars.githubusercontent.com/nicholasgriffintn?size=128',
  'ide-intellij-idea': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/intellijidea.svg',
  'ide-pycharm': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/pycharm.svg',
  'ide-webstorm': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/webstorm.svg',
  'ide-rider': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/rider.svg',
  'ide-goland': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/goland.svg',
  'ide-clion': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/clion.svg',
  'ide-jetbrains-fleet': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/jetbrains.svg',
  'ide-sublime-text': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/sublimetext.svg',
  'ide-notepad++': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/notepadplusplus.svg',
  'ide-visual-studio': 'https://cdn.jsdelivr.net/npm/simple-icons/icons/visualstudio.svg',
  'ide-zed': 'https://avatars.githubusercontent.com/zed-industries?size=128',
  'ide-trae': 'https://www.trae.ai/favicon.svg',
  'ide-pearai': 'https://avatars.githubusercontent.com/nicepkg?size=128',
};

window.obIcon = function (iconId) {
  const url = window.ObIcons[iconId];
  if (!url) return '<div class="ob-row-icon-fallback">' + (iconId || '?')[0].toUpperCase() + '</div>';
  const safe = String(url).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  return '<img src="' + safe + '" alt="" loading="lazy" />';
};

window.catSvg = function (cat) {
  const icons = {
    skills:
      '<svg viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#7c3aed"/><rect x="5" y="5" width="6" height="6" rx="1.5" fill="#fff" opacity="0.85"/><rect x="13" y="5" width="6" height="6" rx="1.5" fill="#fff" opacity="0.6"/><rect x="5" y="13" width="6" height="6" rx="1.5" fill="#fff" opacity="0.6"/><rect x="13" y="13" width="6" height="6" rx="1.5" fill="#fff" opacity="0.85"/></svg>',
    rules:
      '<svg viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#f59e0b"/><path d="M12 3l7 4v5c0 3.9-2.8 7.2-7 9-4.2-1.8-7-5.1-7-9V7l7-4z" stroke="#fff" stroke-width="1.4" fill="none"/><path d="M9 12l2 2 4-5" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    instruct:
      '<svg viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#3b82f6"/><path d="M7 4h7l3 3v13a1 1 0 01-1 1H7a1 1 0 01-1-1V5a1 1 0 011-1z" stroke="#fff" stroke-width="1.4" fill="none"/><path d="M9 9h6M9 12h6M9 15h4" stroke="#fff" stroke-width="1.2" stroke-linecap="round"/></svg>',
    config:
      '<svg viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#6b7280"/><circle cx="12" cy="12" r="3" stroke="#fff" stroke-width="1.4" fill="none"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="#fff" stroke-width="1.2" stroke-linecap="round"/></svg>',
    mcp: '<svg viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#06b6d4"/><rect x="5" y="8" width="6" height="8" rx="1.5" stroke="#fff" stroke-width="1.4" fill="none"/><rect x="13" y="8" width="6" height="8" rx="1.5" stroke="#fff" stroke-width="1.4" fill="none"/><path d="M11 12h2" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/></svg>',
    opportunity:
      '<svg viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#10b981"/><path d="M12 3v10l4.5 4.5" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="9" stroke="#fff" stroke-width="1.4" fill="none"/></svg>',
  };
  return icons[cat] || '';
};

window.ideIconKey = function (label) {
  const m = {
    'VS Code': 'ide-vs-code',
    Cursor: 'ide-cursor',
    Windsurf: 'ide-windsurf',
    Kiro: 'ide-kiro',
    Antigravity: 'ide-antigravity',
    'IntelliJ IDEA': 'ide-intellij-idea',
    PyCharm: 'ide-pycharm',
    WebStorm: 'ide-webstorm',
    Rider: 'ide-rider',
    GoLand: 'ide-goland',
    CLion: 'ide-clion',
    'JetBrains Fleet': 'ide-jetbrains-fleet',
    'Sublime Text': 'ide-sublime-text',
    'Notepad++': 'ide-notepad++',
    'Visual Studio': 'ide-visual-studio',
    Zed: 'ide-zed',
    Trae: 'ide-trae',
    PearAI: 'ide-pearai',
  };
  return m[label] || 'vscode';
};
