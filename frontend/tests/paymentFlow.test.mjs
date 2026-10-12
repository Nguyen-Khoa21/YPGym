import assert from 'node:assert/strict';
import test from 'node:test';

import { shouldPollPayment } from '../src/features/billing/paymentFlow.ts';

test('payment polling stops on terminal states and at the bounded deadline', () => {
  assert.equal(shouldPollPayment('pending'), true);
  for (const status of ['paid', 'failed', 'cancelled', 'expired']) {
    assert.equal(shouldPollPayment(status), false);
  }
  assert.equal(shouldPollPayment('pending', true), false);
});
