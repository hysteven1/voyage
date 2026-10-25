import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { test } from 'node:test';
import { GET, POST } from '../src/app/api/v1/[...path]/route.ts';

test('same-origin API proxy preserves requests and upstream errors without caching', async () => {
  const server = createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    res.writeHead(422, { 'Content-Type': 'application/json', 'X-Request-ID': 'test-id' });
    res.end(JSON.stringify({ url: req.url, method: req.method, body }));
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const previous = process.env.API_INTERNAL_URL;
  process.env.API_INTERNAL_URL = `http://127.0.0.1:${server.address().port}`;
  try {
    const response = await POST(new Request('http://web/api/v1/trips?test=1', {
      method: 'POST', body: JSON.stringify({ travelers: 2 }),
    }));
    assert.equal(response.status, 422);
    assert.equal(response.headers.get('x-request-id'), 'test-id');
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await response.json(), {
      url: '/api/v1/trips?test=1', method: 'POST', body: '{"travelers":2}',
    });
    const get = await GET(new Request('http://web/api/v1/health'));
    assert.equal((await get.json()).method, 'GET');
  } finally {
    if (previous === undefined) delete process.env.API_INTERNAL_URL;
    else process.env.API_INTERNAL_URL = previous;
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});
