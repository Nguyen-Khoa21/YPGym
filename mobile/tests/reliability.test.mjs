import assert from 'node:assert/strict';
import test from 'node:test';

import { QueryClient } from '@tanstack/react-query';

import { goBackOrReplace } from '../src/lib/navigation.ts';
import { clearMemberQueryData, refreshMembershipQueryData } from '../src/lib/query.ts';
import { endMemberSession, restoreMemberSession } from '../src/lib/session.ts';

test('logout clears memory, member queries and stored token before resetting to login', async () => {
  const events = [];
  const client = new QueryClient();
  client.setQueryData(['health'], { status: 'ok' });
  client.setQueryData(['dashboard', 'member-1'], { private: true });
  await endMemberSession({
    clearMemory: () => events.push('memory'),
    clearQueries: () => { clearMemberQueryData(client); events.push('queries'); },
    clearStoredToken: async () => { events.push('storage'); },
    resetNavigation: () => events.push('login'),
  });
  assert.deepEqual(events, ['memory', 'queries', 'storage', 'login']);
  assert.equal(client.getQueryData(['dashboard', 'member-1']), undefined);
  assert.deepEqual(client.getQueryData(['health']), { status: 'ok' });
  client.clear();
});

test('session restore accepts members, preserves retryable sessions and discards expired tokens', async () => {
  let discarded = 0;
  const base = {
    readToken: async () => 'stored-token',
    discardStoredSession: async () => { discarded += 1; },
    isUnauthorized: (error) => error?.status === 401,
  };
  const restored = await restoreMemberSession({ ...base, loadUser: async () => ({ role: 'member', name: 'Maya' }) });
  assert.equal(restored.kind, 'authenticated');

  const retry = await restoreMemberSession({ ...base, loadUser: async () => { throw { status: 0 }; } });
  assert.deepEqual({ kind: retry.kind, token: retry.token }, { kind: 'retry', token: 'stored-token' });
  assert.equal(discarded, 0);

  const expired = await restoreMemberSession({ ...base, loadUser: async () => { throw { status: 401 }; } });
  assert.deepEqual(expired, { kind: 'anonymous' });
  assert.equal(discarded, 1);
});

test('membership refresh replaces active state with cancelled and renewed server state', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  let serverMembership = { status: 'active', expiry_date: '2026-10-01' };
  const key = ['dashboard', 'member-1'];
  const readDashboard = () => client.fetchQuery({ queryKey: key, queryFn: async () => ({ membership: { ...serverMembership } }) });
  await readDashboard();

  serverMembership = { status: 'cancelled', expiry_date: '2026-10-01' };
  await refreshMembershipQueryData(client);
  assert.equal(client.getQueryData(key).membership.status, 'cancelled');

  serverMembership = { status: 'active', expiry_date: '2027-10-01' };
  await refreshMembershipQueryData(client);
  assert.deepEqual(client.getQueryData(key).membership, serverMembership);
  client.clear();
});

test('Back uses stack history and otherwise replaces with the safe route', () => {
  const events = [];
  goBackOrReplace({ canGoBack: () => true, back: () => events.push('back'), replace: (path) => events.push(path) }, '/dashboard');
  goBackOrReplace({ canGoBack: () => false, back: () => events.push('back'), replace: (path) => events.push(path) }, '/dashboard');
  assert.deepEqual(events, ['back', '/dashboard']);
});
