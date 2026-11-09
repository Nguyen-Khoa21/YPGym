import assert from 'node:assert/strict';
import test from 'node:test';

const { mustChangePassword, validatePasswordChange } = await import('../src/lib/forcedPassword.ts');

test('only an explicit flag forces a password change', () => {
  assert.equal(mustChangePassword({ must_change_password: true }), true);
  assert.equal(mustChangePassword({ must_change_password: false }), false);
  assert.equal(mustChangePassword({}), false);
  assert.equal(mustChangePassword(null), false);
});

test('password change validation', () => {
  assert.deepEqual(validatePasswordChange({ current: 'Temp#1234', next: 'NewSecret99', confirm: 'NewSecret99' }), {});
  assert.ok(validatePasswordChange({ current: '', next: 'NewSecret99', confirm: 'NewSecret99' }).current);
  assert.ok(validatePasswordChange({ current: 'Temp#1234', next: 'short', confirm: 'short' }).next);
  assert.ok(validatePasswordChange({ current: 'Temp#1234', next: 'Temp#1234', confirm: 'Temp#1234' }).next);
  assert.ok(validatePasswordChange({ current: 'Temp#1234', next: 'NewSecret99', confirm: 'other' }).confirm);
});
