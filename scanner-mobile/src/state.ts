import type { ScanResult, ScannerError } from './types.ts';

export type ScannerState =
  | { status: 'unprovisioned' }
  | { status: 'camera_permission_required' }
  | { status: 'ready' }
  | { status: 'code_detected' }
  | { status: 'submitting' }
  | { status: 'success'; result: ScanResult }
  | { status: 'known_failure'; error: ScannerError }
  | { status: 'offline'; error: ScannerError }
  | { status: 'device_blocked'; error: ScannerError };

export type ScannerEvent =
  | { type: 'UNPROVISION' }
  | { type: 'PERMISSION_REQUIRED' }
  | { type: 'READY' }
  | { type: 'CODE_DETECTED' }
  | { type: 'SUBMIT' }
  | { type: 'SUCCESS'; result: ScanResult }
  | { type: 'FAILURE'; error: ScannerError }
  | { type: 'OFFLINE'; error: ScannerError }
  | { type: 'DEVICE_BLOCKED'; error: ScannerError };

export const initialState: ScannerState = { status: 'unprovisioned' };

export function shouldAcceptScan(status: ScannerState['status'], locked: boolean) { return status === 'ready' && !locked; }
export function isQrPayloadLengthAllowed(payloadLength: number) { return payloadLength >= 20 && payloadLength <= 4096; }
export function shouldRenderCamera(foreground: boolean, permissionGranted: boolean, status: ScannerState['status']) {
  return foreground && permissionGranted && status === 'ready';
}

export function scannerReducer(state: ScannerState, event: ScannerEvent): ScannerState {
  if (event.type === 'UNPROVISION') return { status: 'unprovisioned' };
  if (event.type === 'DEVICE_BLOCKED') return { status: 'device_blocked', error: event.error };
  if (event.type === 'OFFLINE') return { status: 'offline', error: event.error };
  if (event.type === 'READY') return state.status === 'submitting' ? state : { status: 'ready' };
  if (event.type === 'PERMISSION_REQUIRED' && state.status !== 'submitting') return { status: 'camera_permission_required' };
  if (event.type === 'CODE_DETECTED' && state.status === 'ready') return { status: 'code_detected' };
  if (event.type === 'SUBMIT' && state.status === 'code_detected') return { status: 'submitting' };
  if (event.type === 'SUCCESS' && state.status === 'submitting') return { status: 'success', result: event.result };
  if (event.type === 'FAILURE' && ['ready', 'code_detected', 'submitting'].includes(state.status)) {
    return { status: 'known_failure', error: event.error };
  }
  return state;
}
