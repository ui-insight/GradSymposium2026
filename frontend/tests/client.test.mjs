import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const compile = source => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleUrl = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const storageSource = await readFile(new URL('../src/utils/storage.ts', import.meta.url), 'utf8');
const storageUrl = moduleUrl(compile(storageSource));
const clientSource = await readFile(new URL('../src/api/client.ts', import.meta.url), 'utf8');
const clientUrl = moduleUrl(compile(clientSource.replace("'../utils/storage'", JSON.stringify(storageUrl))));

test('new judge profile uses the newly issued token even when another judge is signed in', async () => {
  const previousFetch = globalThis.fetch;
  const previousWindow = globalThis.window;
  globalThis.window = { localStorage: { getItem: () => 'previous-judge-token' } };
  const authorizations = [];
  globalThis.fetch = async (_url, options) => {
    authorizations.push(options.headers.Authorization);
    return { ok: true, status: 200, json: async () => ({ Judge_ID: 'new-judge' }) };
  };
  try {
    const { apiFetch } = await import(clientUrl);
    const profile = await apiFetch('/judge/me', {
      headers: { Authorization: 'Bearer new-judge-token' },
    });
    assert.equal(profile.Judge_ID, 'new-judge');
    await apiFetch('/judge/projects');
    assert.deepEqual(authorizations, ['Bearer new-judge-token', 'Bearer previous-judge-token']);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  }
});
