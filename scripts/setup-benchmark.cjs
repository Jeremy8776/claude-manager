/**
 * setup-benchmark.cjs — Register fixtures, rebuild index, verify retrieval.
 *
 * Usage:
 *   node scripts/setup-benchmark.cjs
 *
 * This:
 *   1. Registers bench/fixtures/skills/ as a skill source
 *   2. Rebuilds the vector index
 *   3. Runs a quick retrieval health check
 */

const http = require('http');
const path = require('path');

const CE_HOST = '127.0.0.1';
const CE_PORT = 3847;
const FIXTURES = path.resolve(__dirname, '..', 'bench', 'fixtures', 'skills');

function request(method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const payload = body !== undefined ? JSON.stringify(body) : null;
    const opts = {
      host: CE_HOST,
      port: CE_PORT,
      path: urlPath,
      method,
      timeout: 120000,
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

async function main() {
  console.log('=== Benchmark Setup ===\n');

  // Step 1: Register fixtures
  console.log('1. Registering fixture skills...');
  const addResult = await request('POST', '/api/skill-sources', {
    path: FIXTURES,
    label: 'benchmark-fixtures',
  });
  if (addResult.ok) {
    console.log(`   Registered: ${addResult.source.id} -> ${addResult.source.path}`);
  } else if (addResult.error && addResult.error.includes('already linked')) {
    console.log('   Already registered (skipping).');
  } else {
    console.error(`   FAILED: ${addResult.error}`);
    process.exitCode = 1;
    return;
  }

  // Step 2: Rebuild index
  console.log('\n2. Rebuilding vector index...');
  const indexResult = await request('POST', '/api/index');
  if (indexResult.ok) {
    console.log(
      `   Index built: ${indexResult.chunks} chunks, ${indexResult.skills} skills, model=${indexResult.model}`,
    );
  } else {
    console.error(`   FAILED: ${indexResult.error}`);
    process.exitCode = 1;
    return;
  }

  // Step 3: Quick health check
  console.log('\n3. Quick search test...');
  const searchResult = await request('POST', '/api/search', {
    query: 'process CPU usage Windows task manager',
    limit: 5,
  });
  if (searchResult.ok) {
    const ids = (searchResult.results || []).map((r) => r.skillId);
    console.log(`   Top results: ${ids.join(', ')}`);
  } else {
    console.error(`   FAILED: ${searchResult.error}`);
    process.exitCode = 1;
    return;
  }

  console.log('\n=== Setup complete ===');
}

main().catch((err) => {
  console.error('Fatal:', err.message);
  process.exitCode = 1;
});
