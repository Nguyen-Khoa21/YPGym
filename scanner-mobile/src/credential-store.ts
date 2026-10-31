import { parseCredentials, serializeCredentials } from './credentials.ts';
import type { Credentials } from './types.ts';

export interface CredentialStorageAdapter {
  getItemAsync(key: string): Promise<string | null>;
  setItemAsync(key: string, value: string, options?: object): Promise<void>;
  deleteItemAsync(key: string): Promise<void>;
}

export function createCredentialStore(
  adapter: CredentialStorageAdapter,
  options?: object,
  key = 'ypgym_scanner_device_v1',
) {
  return {
    async load() {
      return parseCredentials(await adapter.getItemAsync(key));
    },
    async save(credentials: Credentials) {
      await adapter.setItemAsync(key, serializeCredentials(credentials), options);
    },
    async clear() {
      await adapter.deleteItemAsync(key);
    },
  };
}
