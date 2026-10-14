import assert from 'node:assert/strict';
import test from 'node:test';

import { AppErrorBoundary } from '../src/app/AppErrorBoundary.ts';
import { apiRequest } from '../src/lib/apiClient.ts';
import { ApiError, applyApiFieldErrors, toUiError } from '../src/lib/apiErrors.ts';

test('structured API failures preserve support context and map safe field errors', () => {
  const requestId = '4e090f14-dbd4-412c-ab4f-4f943cd19acd';
  const error = new ApiError(
    'VALIDATION_ERROR',
    'The request could not be validated.',
    422,
    [
      { type: 'string_too_short', loc: ['body', 'name'], msg: 'Name is too short.' },
      { type: 'missing', loc: ['body', 'server_only'], msg: 'Ignored.' },
    ],
    requestId,
  );
  const mapped = [];

  assert.equal(applyApiFieldErrors(error, (field, details) => mapped.push([field, details]), ['name']), true);
  assert.deepEqual(mapped, [['name', { type: 'server', message: 'Name is too short.' }]]);
  assert.deepEqual(toUiError(error), {
    code: 'VALIDATION_ERROR',
    title: 'Validation Error',
    message: 'The request could not be validated.',
    details: error.details,
    status: 422,
    requestId,
  });
});

test('the API client returns typed safe errors for provider and network failures', async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => { globalThis.fetch = originalFetch; });

  globalThis.fetch = async () => new Response(JSON.stringify({
    error: { code: 'CONFLICT', message: 'The record changed.', details: { field: 'status' } },
  }), {
    status: 409,
    headers: { 'content-type': 'application/json', 'x-request-id': 'request-123' },
  });
  await assert.rejects(
    apiRequest('/example'),
    (error) => error instanceof ApiError
      && error.code === 'CONFLICT'
      && error.status === 409
      && error.requestId === 'request-123'
      && error.details.field === 'status',
  );

  globalThis.fetch = async () => new Response('PRIVATE_INTERNAL_STACK', { status: 500 });
  await assert.rejects(
    apiRequest('/example'),
    (error) => error instanceof ApiError
      && error.code === 'HTTP_ERROR'
      && error.message === 'The request failed.'
      && !error.message.includes('PRIVATE'),
  );

  globalThis.fetch = async () => { throw new Error('PRIVATE_NETWORK_DETAIL'); };
  await assert.rejects(
    apiRequest('/example'),
    (error) => error instanceof ApiError
      && error.code === 'NETWORK_ERROR'
      && error.status === 0
      && !error.message.includes('PRIVATE'),
  );
});

test('unexpected errors stay private and the render boundary offers recovery', () => {
  const uiError = toUiError(new Error('PRIVATE_RENDER_STACK'));
  assert.equal(uiError.code, 'UNKNOWN_ERROR');
  assert.equal(uiError.message, 'Something went wrong.');

  const boundary = new AppErrorBoundary({ children: 'application' });
  assert.equal(boundary.render(), 'application');
  boundary.state = AppErrorBoundary.getDerivedStateFromError();
  const fallback = boundary.render();
  assert.equal(fallback.props.role, 'alert');
  const section = fallback.props.children;
  const button = section.props.children.at(-1);
  assert.equal(button.type, 'button');
  assert.equal(button.props.children, 'Reload application');
});
