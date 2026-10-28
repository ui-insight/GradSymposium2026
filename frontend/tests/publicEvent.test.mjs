import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/api/publicPosters.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const publicApi = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

test('landing conference details are fetched without requesting unpublished posters or sending credentials', async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  const event = { Event_Name: 'ASM', Event_Date: '2026-10-31', Event_End_Date: '2026-11-01', Location: 'Venue' };
  globalThis.fetch = async (path, options) => {
    calls.push({ path, options });
    assert.equal(path, '/api/v1/public/event');
    return { ok: true, json: async () => event };
  };
  try {
    const controller = new AbortController();
    assert.deepEqual(await publicApi.fetchPublicEvent(controller.signal), event);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].options.cache, 'no-store');
    assert.equal(calls[0].options.signal, controller.signal);
    assert.equal(calls[0].options.headers, undefined);
  } finally { globalThis.fetch = previousFetch; }
});

test('public event fetch preserves no-event fallback and rejects failed requests', async () => {
  const previousFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ ok: true, json: async () => null });
    assert.equal(await publicApi.fetchPublicEvent(), null);
    globalThis.fetch = async () => ({ ok: false });
    await assert.rejects(publicApi.fetchPublicEvent(), /conference details could not be loaded/i);
  } finally { globalThis.fetch = previousFetch; }
});
