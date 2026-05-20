const assert = require('assert');

const { cors, body, json } = require('../server/lib/http');
const { PORT } = require('../server/lib/config');

// ---- cors ----
function mockRes() {
  const r = { _headers: {} };
  r.setHeader = (name, value) => {
    r._headers[name] = value;
  };
  return r;
}

// GIVEN a request from the allowed localhost origin
const allowedReq = { headers: { origin: `http://localhost:${PORT}` } };
const allowedRes = mockRes();
cors(allowedReq, allowedRes);
assert.strictEqual(
  allowedRes._headers['Access-Control-Allow-Origin'],
  `http://localhost:${PORT}`,
  'cors sets origin header for localhost',
);
assert.strictEqual(
  allowedRes._headers['Access-Control-Allow-Methods'],
  'GET,POST,OPTIONS',
  'cors sets methods header',
);
assert.strictEqual(
  allowedRes._headers['Access-Control-Allow-Headers'],
  'Content-Type',
  'cors sets allow-headers',
);

// GIVEN a request from 127.0.0.1 origin
const loopbackReq = { headers: { origin: `http://127.0.0.1:${PORT}` } };
const loopbackRes = mockRes();
cors(loopbackReq, loopbackRes);
assert.strictEqual(
  loopbackRes._headers['Access-Control-Allow-Origin'],
  `http://127.0.0.1:${PORT}`,
  'cors sets origin for 127.0.0.1',
);

// GIVEN a request from a disallowed origin
const badReq = { headers: { origin: 'http://evil.example.com' } };
const badRes = mockRes();
cors(badReq, badRes);
assert.strictEqual(
  badRes._headers['Access-Control-Allow-Origin'],
  undefined,
  'cors does NOT set origin for disallowed host',
);

// ---- json ----
// GIVEN a response object
let writtenHead = null;
let writtenBody = '';
const jsonRes = {
  writeHead: (status, headers) => {
    writtenHead = { status, headers };
  },
  end: (data) => {
    writtenBody = data;
  },
};
json(jsonRes, { foo: 'bar' });
assert.strictEqual(writtenHead?.status, 200, 'json defaults to status 200');
assert.strictEqual(writtenHead?.headers['Content-Type'], 'application/json', 'json sets Content-Type');
assert.strictEqual(writtenBody, '{"foo":"bar"}', 'json stringifies body');

// GIVEN a custom status code
let statusHead = null;
const statusRes = {
  writeHead: (status, headers) => {
    statusHead = { status, headers };
  },
  end: () => {},
};
json(statusRes, { err: 'nope' }, 404);
assert.strictEqual(statusHead?.status, 404, 'json uses custom status code');

void (async () => {
  // ---- body (JSON parse) ----
  const http = require('http');

  // GIVEN a request with valid JSON body
  const bodyReq = new http.IncomingMessage(new (require('net').Socket)());
  bodyReq.headers = { 'content-type': 'application/json' };
  const bodyPromise = body(bodyReq);
  bodyReq.emit('data', '{"key":"value"}');
  bodyReq.emit('end');
  const bodyData = await bodyPromise;
  assert.strictEqual(bodyData.key, 'value', 'body parses valid JSON');

  // GIVEN empty body
  const emptyReq = new http.IncomingMessage(new (require('net').Socket)());
  emptyReq.headers = { 'content-type': 'application/json' };
  const emptyPromise = body(emptyReq);
  emptyReq.emit('end');
  const emptyData = await emptyPromise;
  assert.deepStrictEqual(emptyData, {}, 'body returns empty object for empty body');

  // GIVEN invalid JSON body
  const badBodyReq = new http.IncomingMessage(new (require('net').Socket)());
  badBodyReq.headers = { 'content-type': 'application/json' };
  const badBodyPromise = body(badBodyReq);
  badBodyReq.emit('data', 'NOT JSON {{{');
  badBodyReq.emit('end');
  const badBodyData = await badBodyPromise;
  assert.strictEqual(badBodyData._parseError, true, 'body sets _parseError for invalid JSON');

  // GIVEN non-JSON content type
  const nonJsonReq = new http.IncomingMessage(new (require('net').Socket)());
  nonJsonReq.headers = { 'content-type': 'text/plain' };
  nonJsonReq.resume = () => {};
  const nonJsonPromise = body(nonJsonReq);
  const nonJsonData = await nonJsonPromise;
  assert.strictEqual(nonJsonData._parseError, true, 'body sets _parseError for non-json content type');
  assert.strictEqual(nonJsonData._contentType, 'text/plain', 'body includes original content type');

  // GIVEN oversized body
  const bigReq = new http.IncomingMessage(new (require('net').Socket)());
  bigReq.headers = { 'content-type': 'application/json' };
  bigReq.destroy = () => {};
  const bigPromise = body(bigReq);
  bigReq.emit('data', 'x'.repeat(1024 * 1024 + 1));
  try {
    await bigPromise;
    assert.fail('expected oversized body to reject');
  } catch (e) {
    assert(e instanceof Error);
    assert.strictEqual(e.message, 'Payload too large', 'body rejects oversized payload');
  }

  console.log('http smoke ok');
})();
