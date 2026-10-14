import assert from 'node:assert/strict';
import test from 'node:test';

import { toUiError } from '../src/lib/apiErrors.ts';
import {
  configurationDraftState,
  managementMutationQueryKeys,
  refreshManagementQueries,
  updateTrainerListForFilter,
} from '../src/lib/managementMutations.ts';

test('management mutations invalidate every connected view before reporting success', async () => {
  const invalidated = [];
  const client = {
    async invalidateQueries({ queryKey }) {
      invalidated.push(queryKey);
    },
  };

  await refreshManagementQueries(client, 'classes');
  assert.deepEqual(invalidated, managementMutationQueryKeys.classes);
  assert.deepEqual(invalidated.filter((key) => key[0] === 'admin'), [
    ['admin', 'classes'],
    ['admin', 'class-trainers'],
    ['admin', 'trainers'],
  ]);
  assert.ok(invalidated.some((key) => key[0] === 'trainer' && key[1] === 'me'));
});

test('trainer list updates immediately and respects the active status filter', () => {
  const active = { id: '1', display_name: 'Alex Coach', is_active: true };
  const inactive = { ...active, is_active: false };
  const other = { id: '2', display_name: 'Jordan Coach', is_active: true };

  assert.deepEqual(updateTrainerListForFilter([other], active, 'true'), [active, other]);
  assert.deepEqual(updateTrainerListForFilter([active, other], inactive, 'true'), [other]);
  assert.deepEqual(updateTrainerListForFilter([other], inactive, 'false'), [inactive, other]);
});

test('configuration drafts require a changed integer inside the documented bounds', () => {
  assert.deepEqual(configurationDraftState('150', 150, 1, 5000), { value: 150, valid: true, changed: false });
  assert.deepEqual(configurationDraftState('200', 150, 1, 5000), { value: 200, valid: true, changed: true });
  assert.equal(configurationDraftState('', 150, 1, 5000).valid, false);
  assert.equal(configurationDraftState('1.5', 150, 1, 5000).valid, false);
  assert.equal(configurationDraftState('5001', 150, 1, 5000).valid, false);
});

test('unexpected client errors do not expose internal exception text', () => {
  const error = toUiError(new Error('postgresql://secret@host internal stack trace'));
  assert.equal(error.code, 'UNKNOWN_ERROR');
  assert.equal(error.message, 'Something went wrong.');
});
