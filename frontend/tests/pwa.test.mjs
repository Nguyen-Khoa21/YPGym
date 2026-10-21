import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const viteConfig = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8');
const manifest = JSON.parse(readFileSync(new URL('../public/manifest.webmanifest', import.meta.url), 'utf8'));
const statusSource = readFileSync(new URL('../src/components/common/PwaStatus.tsx', import.meta.url), 'utf8');

test('production PWA generation keeps development disabled and preserves the existing manifest', () => {
  assert.ok(viteConfig.includes('VitePWA({'));
  assert.ok(viteConfig.includes('devOptions: { enabled: false }'));
  assert.ok(viteConfig.includes('manifest: false'));
  assert.ok(viteConfig.includes('registerType: "prompt"'));
  assert.ok(viteConfig.includes('navigateFallback: "index.html"'));
});

test('all API methods remain network-only and no authenticated response cache is configured', () => {
  for (const method of ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']) {
    assert.ok(viteConfig.includes(`"${method}"`));
  }
  assert.ok(viteConfig.includes('handler: "NetworkOnly"'));
  assert.ok(viteConfig.includes('/api(?:\\/|$)'));
  assert.doesNotMatch(viteConfig, /CacheFirst|CacheOnly|StaleWhileRevalidate/);
});

test('the PWA exposes safe offline and update states', () => {
  assert.ok(statusSource.includes('useRegisterSW'));
  assert.ok(statusSource.includes('updateServiceWorker(true)'));
  assert.ok(statusSource.includes('window.addEventListener("online"'));
  assert.ok(statusSource.includes('window.addEventListener("offline"'));
  assert.ok(statusSource.includes('Sign-in, payments, QR codes, attendance, and account data require a connection.'));
  assert.ok(statusSource.includes('role={needRefresh ? "alert" : "status"}'));
});

test('the existing full-background icons are declared for standard and maskable use', () => {
  assert.equal(manifest.display, 'standalone');
  assert.ok(manifest.icons.some((icon) => icon.sizes === '192x192' && icon.purpose === 'any maskable'));
  assert.ok(manifest.icons.some((icon) => icon.sizes === '512x512' && icon.purpose === 'any maskable'));
});
