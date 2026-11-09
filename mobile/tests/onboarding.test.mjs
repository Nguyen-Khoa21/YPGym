import assert from 'node:assert/strict';
import test from 'node:test';

const { fromBoolean, toBoolean, shouldPromptOnboarding, yesNoOptions } = await import('../src/lib/onboarding.ts');

test('yes and no map to booleans and an unanswered question stays null', () => {
  assert.equal(toBoolean('yes'), true);
  assert.equal(toBoolean('no'), false);
  assert.equal(toBoolean(''), null);
  assert.equal(fromBoolean(true), 'yes');
  assert.equal(fromBoolean(false), 'no');
  assert.equal(fromBoolean(null), '');
  assert.equal(fromBoolean(undefined), '');
  assert.deepEqual(yesNoOptions.map((option) => option.value), ['yes', 'no']);
});

test('the questionnaire is offered only when nothing was answered or skipped, once per session', () => {
  assert.equal(shouldPromptOnboarding('not_started', false), true);
  assert.equal(shouldPromptOnboarding('not_started', true), false);
  for (const status of ['skipped', 'partial', 'complete', undefined]) assert.equal(shouldPromptOnboarding(status, false), false);
});

const { isChangeLocation, isExpiredStatus, renewScreenParams } = await import('../src/lib/expired.ts');

test('only an expired membership shows the renew panel', () => {
  assert.equal(isExpiredStatus('expired'), true);
  for (const status of ['active', 'expiring_soon', 'frozen', 'cancelled', 'revoked', null, undefined]) assert.equal(isExpiredStatus(status), false);
});

test('change location opens renew without a preselected gym', () => {
  assert.deepEqual(renewScreenParams('renew'), {});
  assert.deepEqual(renewScreenParams('change'), { mode: 'change' });
  assert.equal(isChangeLocation('change'), true);
  assert.equal(isChangeLocation(['change']), true);
  assert.equal(isChangeLocation(undefined), false);
});

const { badgeText, bellLabel } = await import('../src/lib/badge.ts');

test('bell badge hides at zero and caps at 99+', () => {
  assert.equal(badgeText(0), '');
  assert.equal(badgeText(undefined), '');
  assert.equal(badgeText(3), '3');
  assert.equal(badgeText(99), '99');
  assert.equal(badgeText(120), '99+');
  assert.equal(bellLabel(3), 'Notifications, 3 unread');
  assert.equal(bellLabel(0), 'Notifications');
});
