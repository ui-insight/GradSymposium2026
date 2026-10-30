import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';
const compile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const moduleUrl = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const storageUrl = moduleUrl(compile(await readFile(new URL('../src/utils/storage.ts', import.meta.url), 'utf8')));
const clientUrl = moduleUrl(compile((await readFile(new URL('../src/api/client.ts', import.meta.url), 'utf8')).replace("'../utils/storage'", JSON.stringify(storageUrl))));
const votingUrl = moduleUrl(compile((await readFile(new URL('../src/api/voting.ts', import.meta.url), 'utf8')).replace("'./client'", JSON.stringify(clientUrl)).replace("'../utils/storage'", JSON.stringify(storageUrl))));
test('browser session handshake is shared, requires cookie acknowledgement and restores the token', async () => {
  const previousWindow = globalThis.window, previousFetch = globalThis.fetch;
  const saved = new Map();
  globalThis.window = { localStorage: { getItem: key => saved.get(key) ?? null, setItem: (key, value) => saved.set(key, value), removeItem: key => saved.delete(key) } };
  let calls = 0;
  globalThis.fetch = async () => { calls++; return { ok: true, json: async () => calls === 1 ? { cookie_ready: false } : { cookie_ready: true, access_token: 'saved-browser-identity' } }; };
  try {
    const { startBrowserVoting } = await import(votingUrl);
    await Promise.all([startBrowserVoting(), startBrowserVoting()]);
    assert.equal(calls, 2);
    assert.equal(saved.get('voter_access_token'), 'saved-browser-identity');
    saved.clear();
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ cookie_ready: false }) });
    await assert.rejects(startBrowserVoting(), /Enable cookies/);
    assert.equal(saved.has('voter_access_token'), false);
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ cookie_ready: true, access_token: 'same-identity-after-reload' }) });
    await startBrowserVoting();
    assert.equal(saved.get('voter_access_token'), 'same-identity-after-reload');
  } finally {
    globalThis.fetch = previousFetch;
    if (previousWindow === undefined) delete globalThis.window; else globalThis.window = previousWindow;
  }
});
