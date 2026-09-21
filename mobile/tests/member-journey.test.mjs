import assert from 'node:assert/strict';
import test from 'node:test';

import { notificationTarget } from '../src/lib/notifications.ts';

test('class reminder opens the matching booking', () => {
  assert.deepEqual(notificationTarget({ action_type: 'class_booking', action_id: 'booking-1' }), {
    pathname: '/(member)/bookings',
    params: { bookingId: 'booking-1' },
  });
});

test('ordinary notifications stay in the inbox', () => {
  assert.equal(notificationTarget({ action_type: null, action_id: null }), null);
  assert.equal(notificationTarget({ action_type: 'class_booking', action_id: null }), null);
});
