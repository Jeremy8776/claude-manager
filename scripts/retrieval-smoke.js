// @ts-check
/**
 * retrieval-smoke.js — Retrieval-quality smoke gate.
 *
 * Connects to CE (starts one if --start is given), registers fixture skills,
 * rebuilds the vector index, then verifies expected_source Recall@8 = 1.00
 * for every task in gold-answers.json. Exits non-zero on failure.
 *
 * Usage:
 *   node scripts/retrieval-smoke.js                          # connect to existing CE
 *   node scripts/retrieval-smoke.js --port 3847               # specify port
 *   node scripts/retrieval-smoke.js --start                   # start CE then test
 *   node scripts/retrieval-smoke.js --fixtures bench/fixtures/skills
 */

const http = require('http');
const path = require('path');
const fs = require('fs');

const HERE = path.resolve(__dirname, '..');
const GOLD = path.join(HERE, 'bench', 'gold-answers.json');
const TASKS = path.join(HERE, 'bench', 'tasks.json');
const FIXTURES = path.join(HERE, 'bench', 'fixtures', 'skills');
const REQUEST_TIMEOUT_MS = Number(process.env.CE_RETRIEVAL_SMOKE_TIMEOUT_MS || 300000);

/** @type {import('http').Server | null} */
let server = null;
let activePort = 3847;

/**
 * @param {string} method
 * @param {string} urlPath
 * @param {unknown=} body
 */
function request(method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const payload = body !== undefined ? JSON.stringify(body) : null;
    const opts = {
      host: '127.0.0.1',
      port: activePort,
      path: urlPath,
      method,
      timeout: REQUEST_TIMEOUT_MS,
      headers: payload
        ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
        : {},
    };
    const req = http.request(opts, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          reject(new Error(`Invalid JSON: ${data.slice(0, 200)}`));
        }
      });
    });
    req.on('timeout', () => req.destroy(new Error('Request timed out')));
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function run() {
  // Re-parse args inside run scope
  const innerArgv = process.argv.slice(2);
  let innerPort = 3847;
  let innerStart = false;
  let fixtureArg = FIXTURES;
  for (let i = 0; i < innerArgv.length; i++) {
    if (innerArgv[i] === '--port') {
      innerPort = parseInt(/** @type {string} */ (innerArgv[i + 1]), 10) || innerPort;
      i++;
    }
    if (innerArgv[i] === '--start') {
      innerStart = true;
    }
    if (innerArgv[i] === '--fixtures') {
      fixtureArg = path.resolve(HERE, /** @type {string} */ (innerArgv[i + 1]));
      i++;
    }
  }
  const fixturePath = fixtureArg;

  // Validate inputs
  const gold = JSON.parse(fs.readFileSync(GOLD, 'utf8'));
  const tasks = JSON.parse(fs.readFileSync(TASKS, 'utf8'));
  const tasksGold = gold.tasks || {};

  console.log(`Retrieval smoke gate`);
  console.log(`  Fixtures: ${fixturePath}`);
  console.log(`  CE port:  ${innerPort}`);
  console.log(`  Tasks:    ${tasks.length}`);
  console.log();

  activePort = innerPort;

  if (innerStart) {
    process.env.CE_PORT = String(innerPort);
    const { PORT } = require('../server/lib/config');
    const { startServer } = require('../server/server');
    const srv = startServer({ port: PORT, refresh: false });
    await new Promise((resolve) => srv.once('listening', resolve));
    server = srv;
    console.log('  CE started on port', PORT);
  }

  // Verify CE is reachable
  try {
    const hc = await request('GET', `/api/health`);
    if (!hc?.skills) {
      throw new Error('CE health check failed');
    }
    console.log(`  CE reachable: ${Object.keys(hc.skills || {}).length} skill counts`);
  } catch (e) {
    throw new Error(`CE not reachable on port ${innerPort}: ${e instanceof Error ? e.message : String(e)}`);
  }

  try {
    // Register fixture skills as a source
    const addResult = await request('POST', '/api/skill-sources', {
      path: fixturePath,
      label: 'benchmark-fixtures',
    });
    if (!addResult.ok && !addResult.error.includes('already linked')) {
      throw new Error(`Failed to add fixtures: ${addResult.error}`);
    }
    console.log('  Fixtures registered.');

    // Rebuild vector index
    console.log('  Rebuilding index...');
    const indexResult = await request('POST', '/api/index');
    if (!indexResult.ok) {
      throw new Error(`Index rebuild failed: ${indexResult.error}`);
    }
    console.log(`  Index built: ${indexResult.chunks} chunks, ${indexResult.skills} skills`);

    // Test each task
    let failures = 0;
    let totalExpected = 0;
    let totalFound = 0;

    for (const task of tasks) {
      const tid = task.id;
      const goldTask = tasksGold[tid];
      if (!goldTask) {
        console.log(`  ⚠  ${tid}: no gold data, skipping`);
        continue;
      }

      const expected = goldTask.expected_sources || [];
      if (!expected.length) {
        console.log(`  ✓  ${tid}: no expected sources`);
        continue;
      }

      totalExpected += expected.length;

      // Use a generous limit to ensure we catch everything
      const searchResult = await request('POST', '/api/search', {
        query: task.prompt,
        limit: 8,
      });

      // External sources prefix skillIds as `<sourceId>:<bareId>`.
      // Accept both prefixed and bare matches.
      const retrieved = (searchResult.results || []).map(/** @param {any} r */ (r) => r.skillId);
      const uniqueRetrieved = [...new Set(retrieved)];
      /** @param {string} expectedId */
      const matches = (expectedId) =>
        uniqueRetrieved.some((rid) => rid === expectedId || rid.endsWith(':' + expectedId));
      const hits = expected.filter((/** @type {string} */ s) => matches(s));

      totalFound += hits.length;

      if (hits.length === expected.length) {
        console.log(`  ✓  ${tid}: R@8 = ${hits.length}/${expected.length} ${JSON.stringify(expected)}`);
      } else {
        failures++;
        const missed = expected.filter((/** @type {string} */ s) => !matches(s));
        console.log(
          `  ✗  ${tid}: R@8 = ${hits.length}/${expected.length} — missed: ${JSON.stringify(missed)}`,
        );
        console.log(`       retrieved: ${JSON.stringify(uniqueRetrieved)}`);
      }
    }

    const recall = totalExpected > 0 ? totalFound / totalExpected : 1;
    console.log();
    console.log(`  Overall R@8: ${(recall * 100).toFixed(1)}% (${totalFound}/${totalExpected})`);

    if (failures > 0) {
      console.log(`\n  FAIL: ${failures} task(s) with incomplete retrieval`);
      process.exitCode = 1;
    } else if (recall < 1.0) {
      console.log(`\n  FAIL: Overall R@8 < 1.00`);
      process.exitCode = 1;
    } else {
      console.log(`\n  PASS: All tasks achieve R@8 = 1.00`);
    }
  } finally {
    if (server !== null) server.close();
  }
}

run().catch((error) => {
  console.error('Fatal:', error.message);
  process.exitCode = 1;
});
