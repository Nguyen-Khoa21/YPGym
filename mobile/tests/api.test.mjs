import assert from 'node:assert/strict';
import test from 'node:test';

process.env.EXPO_PUBLIC_API_URL = 'http://localhost:8001/api/v1';
const { ApiError, apiRequest, errorMessage } = await import('../src/lib/api.ts?error-contract');

test('mobile API errors preserve safe details and request IDs', async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => new Response(JSON.stringify({
    error: {
      code: 'VALIDATION_ERROR',
      message: 'Check the submitted fields.',
      details: [{ loc: ['body', 'name'], msg: 'Required.' }],
    },
  }), {
    status: 422,
    headers: { 'content-type': 'application/json', 'x-request-id': 'mobile-request-1' },
  });

  await assert.rejects(
    apiRequest('/example'),
    (error) => error instanceof ApiError
      && error.status === 422
      && error.code === 'VALIDATION_ERROR'
      && error.requestId === 'mobile-request-1'
      && error.details[0].loc[1] === 'name',
  );
});

test('mobile network and unexpected errors do not expose internal text', async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async () => { throw new Error('PRIVATE_NETWORK_DETAIL'); };

  await assert.rejects(
    apiRequest('/example'),
    (error) => error instanceof ApiError
      && error.code === 'NETWORK_ERROR'
      && !error.message.includes('PRIVATE'),
  );
  assert.equal(errorMessage(new Error('PRIVATE_RENDER_DETAIL')), 'Something went wrong. Please try again.');
});
