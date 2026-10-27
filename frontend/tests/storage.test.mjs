import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/storage.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});

test('login remains usable when storage reads succeed but writes fail', async () => {
  let storedToken = null;
  globalThis.window = {
    localStorage: {
      getItem: () => storedToken,
      setItem: () => { throw new Error('Quota exceeded'); },
      removeItem: () => { throw new Error('Storage blocked'); },
    },
  };
  try {
    const { storage } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
    storage.setItem('access_token', 'session-token');
    assert.equal(storage.getItem('access_token'), 'session-token');
    storage.removeItem('access_token');
    assert.equal(storage.getItem('access_token'), null);
    storedToken = 'expired-token';
    storage.setItem('access_token', 'fresh-token');
    assert.equal(storage.getItem('access_token'), 'fresh-token');
    storage.removeItem('access_token');
    assert.equal(storage.getItem('access_token'), null);
  } finally {
    delete globalThis.window;
  }
});
