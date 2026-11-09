import assert from 'node:assert/strict';
import test from 'node:test';

import { QueryClient } from '@tanstack/react-query';

process.env.EXPO_PUBLIC_API_URL = 'http://localhost:8001/api/v1';
const { ApiError, errorMessage } = await import('../src/lib/api.ts?gym-errors');
const { attendanceBenefitPath, gymChangeNotice, gymNameFor, renewalCheckoutBody, renewalGymId, withGymParam } = await import('../src/lib/gyms.ts');
const { clearMemberQueryData, refreshMembershipQueryData } = await import('../src/lib/query.ts');

const d1 = { id: 'gym-1', name: 'District 1', is_active: true };
const d11 = { id: 'gym-11', name: 'District 11', is_active: true };
const closed = { id: 'gym-x', name: 'Closed Gym', is_active: false };

test('gym id is appended to a path with or without an existing query string', () => {
  assert.equal(withGymParam('/classes/upcoming', 'gym-11'), '/classes/upcoming?gym_id=gym-11');
  assert.equal(withGymParam('/a?plan_id=p1', 'gym-11'), '/a?plan_id=p1&gym_id=gym-11');
  assert.equal(withGymParam('/classes/upcoming', null), '/classes/upcoming');
  assert.equal(withGymParam('/classes/upcoming', undefined), '/classes/upcoming');
});

test('renewal defaults to the previous home gym and honours a pick (AC-MOB-002)', () => {
  const gyms = [d1, d11, closed];
  assert.equal(renewalGymId(gyms, null, 'gym-1'), 'gym-1');
  assert.equal(renewalGymId(gyms, 'gym-11', 'gym-1'), 'gym-11');
});

test('renewal never offers an inactive gym and a first purchase must pick one', () => {
  const gyms = [d1, d11, closed];
  assert.equal(renewalGymId(gyms, 'gym-x', 'gym-1'), 'gym-1');
  assert.equal(renewalGymId(gyms, null, 'gym-x'), null);
  assert.equal(renewalGymId(gyms, null, undefined), null);
  assert.equal(renewalGymId([], null, 'gym-1'), null);
});

test('when the gym list is unavailable the pick or home gym is passed through for the backend to judge', () => {
  assert.equal(renewalGymId(undefined, null, 'gym-1'), 'gym-1');
  assert.equal(renewalGymId(undefined, 'gym-11', 'gym-1'), 'gym-11');
  assert.equal(renewalGymId(undefined, null, null), null);
});

test('both renewal requests carry the chosen gym (AC-MOB-002)', () => {
  assert.equal(attendanceBenefitPath('plan-1', 'gym-11'), '/memberships/attendance-benefit/me?plan_id=plan-1&gym_id=gym-11');
  assert.deepEqual(renewalCheckoutBody('plan-1', 'gym-11', 'mobile'), { membership_plan_id: 'plan-1', gym_id: 'gym-11', client_platform: 'mobile' });
  assert.equal(attendanceBenefitPath('plan-1', null), '/memberships/attendance-benefit/me?plan_id=plan-1');
  assert.deepEqual(renewalCheckoutBody('plan-1', null, 'mobile_web'), { membership_plan_id: 'plan-1', client_platform: 'mobile_web' });
});

test('gym names resolve from the loaded list', () => {
  assert.equal(gymNameFor([d1, d11], 'gym-11'), 'District 11');
  assert.equal(gymNameFor([d1], 'gym-11'), null);
  assert.equal(gymNameFor(undefined, 'gym-1'), null);
  assert.equal(gymNameFor([d1], null), null);
});

test('confirmation says the home gym changes only after payment succeeds (FR-MOB-004)', () => {
  assert.match(gymChangeNotice('District 11', 'gym-11', 'District 1', 'gym-1'), /changes to District 11 only after payment succeeds.*keep using District 1/);
  assert.match(gymChangeNotice('District 1', 'gym-1', 'District 1', 'gym-1'), /only changes after a payment succeeds/);
  assert.match(gymChangeNotice('District 1', 'gym-1', null, null), /only changes after a payment succeeds/);
});

test('gym refusals show clear member messages and other errors are untouched (FR-MOB-007, AC-MOB-003)', () => {
  const api = (status, code, message) => new ApiError(message, status, code);
  assert.match(errorMessage(api(422, 'GYM_SELECTION_REQUIRED', 'Select an active gym location before starting checkout.')), /Choose the gym you want to join/);
  assert.match(errorMessage(api(403, 'MEMBERSHIP_GYM_MISMATCH', 'This membership is not eligible for the scanner\'s gym location.')), /different gym.*home gym/i);
  assert.match(errorMessage(api(403, 'ATTENDANCE_GYM_MISMATCH', 'x')), /checked in at a different/i);
  assert.match(errorMessage(api(409, 'CLASS_GYM_INACTIVE', 'This class\'s gym location is inactive.')), /not taking bookings/i);
  assert.match(errorMessage(api(404, 'RESOURCE_NOT_FOUND', 'The selected gym location was not found or is inactive.')), /no longer available.*another gym/i);
  assert.equal(errorMessage(api(404, 'RESOURCE_NOT_FOUND', 'Membership plan was not found.')), 'Membership plan was not found.');
  assert.equal(errorMessage(api(500, 'HTTP_ERROR', 'Backend text.')), 'Backend text.');
  assert.equal(errorMessage(new Error('PRIVATE')), 'Something went wrong. Please try again.');
});

test('payment success refreshes the gym and class data without a restart (AC-MOB-004)', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  let home = 'District 1';
  const gymKey = ['gym', 'me', 'member-1'];
  const classesKey = ['classes', 'member-1', 'gym-1'];
  await client.fetchQuery({ queryKey: gymKey, queryFn: async () => ({ name: home }) });
  await client.fetchQuery({ queryKey: classesKey, queryFn: async () => ({ gym: home }) });

  home = 'District 11';
  await refreshMembershipQueryData(client);
  assert.equal(client.getQueryData(gymKey).name, 'District 11');
  assert.equal(client.getQueryData(classesKey).gym, 'District 11');
  client.clear();
});

test('logout drops the member gym but keeps shared data', () => {
  const client = new QueryClient();
  client.setQueryData(['gym', 'me', 'member-1'], { name: 'District 1' });
  client.setQueryData(['plans'], []);
  clearMemberQueryData(client);
  assert.equal(client.getQueryData(['gym', 'me', 'member-1']), undefined);
  assert.deepEqual(client.getQueryData(['plans']), []);
  client.clear();
});
