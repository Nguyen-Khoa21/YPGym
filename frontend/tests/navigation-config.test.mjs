import assert from 'node:assert/strict';
import test from 'node:test';

import {
  memberMobileNavigation,
  memberNavigation,
  navigationForRole,
  operationsNavigation,
  publicNavigation,
  workforceNavigationForRole,
} from '../src/app/navigation.ts';
import { routeFor, routePaths } from '../src/app/routes.ts';
import { workspacePathForRole } from '../src/features/auth/workspace.ts';

const configuredPaths = new Set(Object.values(routePaths));

test('route names remain unique and dynamic route builders encode identifiers', () => {
  assert.equal(configuredPaths.size, Object.values(routePaths).length);
  assert.equal(routeFor.membershipPurchase('plan/one'), '/memberships/buy/plan%2Fone');
  assert.equal(routeFor.memberTrainingDetail('exercise one'), '/app/train/exercise%20one');
  assert.equal(routeFor.adminMemberDetail('member/one'), '/admin/members/member%2Fone');
});

test('every configured navigation destination uses a canonical route', () => {
  const items = [
    ...publicNavigation,
    ...memberNavigation,
    ...operationsNavigation,
    ...workforceNavigationForRole('staff'),
    ...workforceNavigationForRole('pt'),
  ];
  for (const item of items) assert.ok(configuredPaths.has(item.to), item.to);
});

test('member mobile navigation is an explicit five-item subset', () => {
  assert.deepEqual(
    memberMobileNavigation.map((item) => [item.to, item.mobileLabel]),
    [
      [routePaths.memberDashboard, 'Dashboard'],
      [routePaths.memberQr, 'QR'],
      [routePaths.memberClasses, 'Classes'],
      [routePaths.memberTraining, 'YPTrain'],
      [routePaths.memberProfile, 'Profile'],
    ],
  );
});

test('operations navigation mirrors current client role visibility without granting backend access', () => {
  const manager = navigationForRole(operationsNavigation, 'manager');
  const admin = navigationForRole(operationsNavigation, 'admin');
  const staff = navigationForRole(operationsNavigation, 'staff');

  assert.ok(manager.some((item) => item.to === routePaths.adminMembers && item.dashboard));
  assert.ok(!manager.some((item) => item.to === routePaths.adminBilling));
  assert.ok(!manager.some((item) => item.to === routePaths.adminClasses));
  assert.ok(admin.some((item) => item.to === routePaths.adminBilling));
  assert.ok(admin.some((item) => item.to === routePaths.adminClasses));
  assert.deepEqual(
    staff.map((item) => item.to),
    [routePaths.operationsHome, routePaths.adminAttendance, routePaths.staffTimeClock],
  );
});

test('workspace destinations stay role-specific', () => {
  assert.equal(workspacePathForRole('member'), routePaths.memberDashboard);
  assert.equal(workspacePathForRole('staff'), routePaths.staffTimeClock);
  assert.equal(workspacePathForRole('manager'), routePaths.operationsHome);
  assert.equal(workspacePathForRole('admin'), routePaths.operationsHome);
  assert.equal(workspacePathForRole('pt'), routePaths.ptDashboard);
});
