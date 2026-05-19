// @ts-check
// system-scan-definitions.js — Static host, file, IDE, and extension probes.

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

// null = host has no standard global config file to create
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

module.exports = {
  HOSTS,
  RULE_FILE_NAMES,
  INSTRUCTION_FILE_NAMES,
  CONFIG_FILE_NAMES,
  OPPORTUNITY_FILES,
  IDE_PROBE_PATHS,
  AI_EXTENSION_PATTERNS,
};
