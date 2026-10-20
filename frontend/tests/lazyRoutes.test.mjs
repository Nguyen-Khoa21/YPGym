import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const routerSource = readFileSync(new URL('../src/app/router.tsx', import.meta.url), 'utf8');
const appSource = readFileSync(new URL('../src/app/App.tsx', import.meta.url), 'utf8');

const lazyRoutes = [
  ['AdminAttendancePage', '/admin/attendance', '[...operationsRoles]'],
  ['AdminTrainingPage', '/admin/exercises', '[...managerRoles]'],
  ['AdminBillingPage', '/admin/billing', '["admin"]'],
  ['AdminAuditPage', '/admin/audit', '[...managerRoles]'],
  ['MemberTrainingPage', '/app/train', '["member"]'],
];

test('measured heavy routes are lazy while their authorization wrappers remain intact', () => {
  for (const [component, path, roles] of lazyRoutes) {
    assert.match(routerSource, new RegExp(`const ${component} = lazy\\(`));
    assert.doesNotMatch(routerSource, new RegExp(`import \\{ ${component} \\} from`));
    assert.ok(routerSource.includes(`path: "${path}"`));
    assert.ok(routerSource.includes(`<ProtectedRoute roles={${roles}}><${component} /></ProtectedRoute>`));
  }
});

test('critical and recovery routes stay eager', () => {
  for (const component of ['LoginPage', 'MemberDashboardPage', 'MemberQrPage', 'PaymentResultPage']) {
    assert.match(routerSource, new RegExp(`import \\{ ${component} \\} from`));
    assert.doesNotMatch(routerSource, new RegExp(`const ${component} = lazy\\(`));
  }
});

test('lazy routes share an accessible loading fallback and render failures retain reload recovery', () => {
  assert.ok(appSource.includes('<Suspense fallback={<RouteLoadingFallback />}>'));
  assert.ok(appSource.includes('<LoadingState'));
  assert.ok(appSource.includes('id="main-content"'));

  const boundarySource = readFileSync(new URL('../src/app/AppErrorBoundary.ts', import.meta.url), 'utf8');
  assert.ok(boundarySource.includes('window.location.reload()'));
  assert.ok(boundarySource.includes('role: "alert"'));
});
