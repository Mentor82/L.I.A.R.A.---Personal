import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeChatTask, chatTaskOptions, selectOptimalModel, modelDisplayName } from './chatTasks.js';

test('mobile task labels remain distinguishable', () => {
  assert.equal(modelDisplayName('task:tool'), 'task:tool');
  assert.equal(modelDisplayName('task:private'), 'task:private');
  assert.equal(modelDisplayName('llama3.2:3b'), 'llama3.2');
});

test('legacy persisted IDs and empty preferences migrate to tool task', () => {
  for (const value of [null, '', 'llama3.2:3b', 'gpt-oss:120b-cloud', 'task:', 'task:bad value']) {
    assert.equal(normalizeChatTask(value), 'task:tool');
  }
  assert.equal(normalizeChatTask('task:private'), 'task:private');
});

test('mixed API results expose tasks only, outage fallback also uses tasks', () => {
  assert.deepEqual(chatTaskOptions([{ name: 'llama3.2:3b' }, { name: 'task:private' }]),
    [{ name: 'task:private' }]);
  for (const models of [null, [], [{ name: 'gpt-oss:120b-cloud' }]]) {
    assert.ok(chatTaskOptions(models).every(m => m.name.startsWith('task:')));
  }
});

test('automatic selection routes quick chat and complex tasks without model IDs', () => {
  assert.equal(selectOptimalModel('Hallo'), 'task:fast');
  assert.equal(selectOptimalModel('Schreibe eine Python Funktion'), 'task:tool');
  assert.equal(selectOptimalModel('Erkläre diese Analyse'), 'task:tool');
  assert.equal(selectOptimalModel('x '.repeat(25)), 'task:tool');
});
