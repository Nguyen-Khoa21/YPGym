import * as SecureStore from 'expo-secure-store';

import type { Credentials } from './types.ts';
import { createCredentialStore } from './credential-store';

const credentialStore = createCredentialStore(SecureStore, {
  keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
});

export async function loadCredentials(): Promise<Credentials | null> {
  return credentialStore.load();
}

export async function saveCredentials(credentials: Credentials) {
  await credentialStore.save(credentials);
}

export async function clearCredentials() { await credentialStore.clear(); }
