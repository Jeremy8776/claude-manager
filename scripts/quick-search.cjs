/**
 * quick-search.cjs — Quick search test against running CE.
 * Usage: node scripts/quick-search.cjs [port=3847]
 */
const http = require('http');
const port = parseInt(process.argv[2], 10) || 3847;
const query = process.argv[3] || 'What is using my CPU right now and how do I find the worst offender?';

function request(method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const payload = body ? JSON.stringify(body) : null;
    const opts = {
      host: '127.0.0.1',
      port,
      path: urlPath,
      method,
      timeout: 30000,
      headers: payload
        ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
        : {},
    };
    const req = http.request(opts, (res) => {
      let d = '';
      res.on('data', (c) => (d += c));
      res.on('end', () => {
        try {
          resolve(JSON.parse(d));
        } catch {
          reject(new Error(d.slice(0, 200)));
        }
      });
    });
    req.on('timeout', () => req.destroy(new Error('Timeout')));
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

request('POST', '/api/search', { query, limit: 10 }).then((data) => {
  (data.results || []).forEach((r, i) =>
    console.log(
      `${i + 1}. ${r.skillId} (score=${(r.score || 0).toFixed(3)}, lex=${(r.lexicalScore || 0).toFixed(3)}) — ${r.section}`,
    ),
  );
});
