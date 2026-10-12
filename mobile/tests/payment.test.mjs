import assert from 'node:assert/strict';
import test from 'node:test';

import { shouldPollPayment } from '../src/lib/payment.ts';

test('VNPay status polling stops on final states and after its deadline', () => {
  assert.equal(shouldPollPayment('pending'), true);
  for (const status of ['paid', 'failed', 'cancelled', 'expired']) assert.equal(shouldPollPayment(status), false);
  assert.equal(shouldPollPayment('pending', true), false);
});
