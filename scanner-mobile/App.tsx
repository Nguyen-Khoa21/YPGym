import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import { useKeepAwake } from 'expo-keep-awake';
import { StatusBar } from 'expo-status-bar';
import {
  Alert,
  AppState,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { submitScan, ScannerApiError, verifyDevice } from './src/api';
import { initialActionForMode } from './src/credentials';
import { isDeviceBlocked, isNetworkError, staffGuidance } from './src/errors';
import { buildSuccessPresentation } from './src/presentation';
import { initialState, isQrPayloadLengthAllowed, scannerReducer, shouldAcceptScan, shouldRenderCamera } from './src/state';
import { clearCredentials, loadCredentials, saveCredentials } from './src/storage';
import type { Action, Credentials, ScannerMode, ScanResult } from './src/types';

const ORANGE = '#ff6b1a';
const GREEN = '#36d399';
const DEFAULT_URL = process.env.EXPO_PUBLIC_API_URL ?? '';
const GYM_TIMEZONE = process.env.EXPO_PUBLIC_GYM_TIMEZONE ?? 'Asia/Ho_Chi_Minh';

export default function App() {
  const [state, dispatch] = useReducer(scannerReducer, initialState);
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [deviceName, setDeviceName] = useState('');
  const [action, setAction] = useState<Action>('check_in');
  const [permission, requestPermission] = useCameraPermissions();
  const [foreground, setForeground] = useState(AppState.currentState === 'active');
  const scanLocked = useRef(false);

  const resetReady = useCallback(() => {
    scanLocked.current = false;
    dispatch({ type: permission?.granted ? 'READY' : 'PERMISSION_REQUIRED' });
  }, [permission?.granted]);

  const validate = useCallback(async (value: Credentials) => {
    try {
      const device = await verifyDevice(value);
      setCredentials(value);
      setDeviceName(device.display_name);
      setAction(initialActionForMode(value.mode));
      scanLocked.current = false;
      dispatch({ type: permission?.granted ? 'READY' : 'PERMISSION_REQUIRED' });
      return true;
    } catch (error) {
      const scannerError = normalizeError(error);
      dispatch(isDeviceBlocked(scannerError.code)
        ? { type: 'DEVICE_BLOCKED', error: scannerError }
        : { type: 'OFFLINE', error: scannerError });
      return false;
    }
  }, [permission?.granted]);

  useEffect(() => {
    let mounted = true;
    void loadCredentials().then(async (stored) => {
      if (!mounted) return;
      if (!stored) { dispatch({ type: 'UNPROVISION' }); return; }
      setCredentials(stored);
      await validate(stored);
    });
    return () => { mounted = false; };
  }, [validate]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (next) => {
      setForeground(next === 'active');
      scanLocked.current = true;
      if (next === 'active' && credentials) void validate(credentials);
    });
    return () => subscription.remove();
  }, [credentials, validate]);

  useEffect(() => {
    if (credentials && permission?.granted && state.status === 'camera_permission_required') resetReady();
  }, [credentials, permission?.granted, resetReady, state.status]);

  useEffect(() => {
    if (state.status !== 'success') return;
    const timer = setTimeout(resetReady, 4000);
    return () => clearTimeout(timer);
  }, [resetReady, state.status]);

  const onProvision = async (value: Credentials) => {
    if (await validate(value)) await saveCredentials(value);
  };

  const onScan = async ({ data }: BarcodeScanningResult) => {
    if (!credentials || !shouldAcceptScan(state.status, scanLocked.current)) return;
    scanLocked.current = true;
    if (!isQrPayloadLengthAllowed(data.length)) {
      dispatch({ type: 'FAILURE', error: { code: 'INVALID_TOKEN', message: 'The QR payload length is invalid.' } });
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      return;
    }
    dispatch({ type: 'CODE_DETECTED' });
    dispatch({ type: 'SUBMIT' });
    try {
      const result = await submitScan(credentials, action, data);
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      dispatch({ type: 'SUCCESS', result });
    } catch (error) {
      const scannerError = normalizeError(error);
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      if (isNetworkError(scannerError.code)) dispatch({ type: 'OFFLINE', error: scannerError });
      else if (isDeviceBlocked(scannerError.code)) dispatch({ type: 'DEVICE_BLOCKED', error: scannerError });
      else dispatch({ type: 'FAILURE', error: scannerError });
    }
  };

  const resetDevice = () => Alert.alert('Remove scanner credentials?', 'This phone will need to be provisioned again.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Remove', style: 'destructive', onPress: () => void clearCredentials().then(() => { setCredentials(null); setDeviceName(''); dispatch({ type: 'UNPROVISION' }); }) },
  ]);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <Pressable accessibilityRole="button" accessibilityLabel="YPGym Scanner. Hold to reset device." onLongPress={resetDevice} delayLongPress={1800}>
        <Text style={styles.brand}>YPGYM <Text style={styles.orange}>SCANNER</Text></Text>
      </Pressable>
      {state.status === 'unprovisioned' || !credentials
        ? <ProvisionScreen onProvision={onProvision} />
        : <ScannerScreen
            state={state}
            credentials={credentials}
            deviceName={deviceName}
            action={action}
            setAction={setAction}
            foreground={foreground}
            permissionGranted={Boolean(permission?.granted)}
            requestPermission={() => void requestPermission()}
            onScan={(result) => void onScan(result)}
            onReset={resetReady}
            onRetry={() => void validate(credentials)}
          />}
    </SafeAreaView>
  );
}

function ScannerScreen({ state, credentials, deviceName, action, setAction, foreground, permissionGranted, requestPermission, onScan, onReset, onRetry }: {
  state: ReturnType<typeof scannerReducer>; credentials: Credentials; deviceName: string; action: Action; setAction: (action: Action) => void;
  foreground: boolean; permissionGranted: boolean; requestPermission: () => void; onScan: (result: BarcodeScanningResult) => void;
  onReset: () => void; onRetry: () => void;
}) {
  useKeepAwake();
  const online = !['offline', 'device_blocked'].includes(state.status);
  return <View style={styles.body}>
    <View style={styles.deviceRow}>
      <View style={[styles.dot, { backgroundColor: online ? GREEN : '#ef4444' }]} />
      <Text style={styles.muted}>{deviceName || safeDeviceId(credentials.deviceId)} · {online ? 'Online' : 'Unavailable'}</Text>
    </View>
    {credentials.mode === 'both' ? <View style={styles.modeRow}>
      <ModeButton label="Check in" selected={action === 'check_in'} onPress={() => setAction('check_in')} />
      <ModeButton label="Check out" selected={action === 'check_out'} onPress={() => setAction('check_out')} />
    </View> : <Text style={styles.lockedMode}>{credentials.mode === 'check_in' ? 'CHECK-IN ONLY' : 'CHECK-OUT ONLY'}</Text>}

    {state.status === 'camera_permission_required' || !permissionGranted
      ? <Panel title="Camera access needed" detail="The camera is used only to read the member's rotating attendance QR." action="Allow camera" onPress={requestPermission} />
      : state.status === 'success'
        ? <Success result={state.result} onReset={onReset} />
        : state.status === 'known_failure'
          ? <Panel title="Scan not accepted" detail={staffGuidance(state.error)} requestId={state.error.requestId} action="Scan next" onPress={onReset} />
          : state.status === 'offline'
            ? <Panel title="Scanner offline" detail="No attendance was recorded. Restore the connection, then scan a fresh QR." requestId={state.error.requestId} action="Retry connection" onPress={onRetry} />
            : state.status === 'device_blocked'
              ? <Panel title="Device unavailable" detail={staffGuidance(state.error)} requestId={state.error.requestId} action="Retry verification" onPress={onRetry} />
              : <View style={styles.cameraShell}>
                  {shouldRenderCamera(foreground, permissionGranted, state.status) ? <CameraView style={StyleSheet.absoluteFill} facing="back" barcodeScannerSettings={{ barcodeTypes: ['qr'] }} onBarcodeScanned={onScan} /> : null}
                  <View pointerEvents="none" style={styles.target} />
                  {state.status === 'submitting' || state.status === 'code_detected' ? <View style={styles.freeze}><Text style={styles.freezeText}>RECORDING…</Text></View> : null}
                </View>}
    {state.status === 'ready' ? <Text style={styles.instruction}>Ask the member to show My QR</Text> : null}
  </View>;
}

function ProvisionScreen({ onProvision }: { onProvision: (credentials: Credentials) => Promise<void> }) {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_URL);
  const [deviceId, setDeviceId] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [mode, setMode] = useState<ScannerMode>('both');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    const normalizedUrl = apiBaseUrl.trim().replace(/\/$/, '');
    if (!/^https?:\/\//.test(normalizedUrl) || deviceId.trim().length < 3 || apiKey.length < 24) {
      Alert.alert('Check provisioning details', 'Enter a complete API URL, device ID, and a device key of at least 24 characters.');
      return;
    }
    setBusy(true);
    try { await onProvision({ apiBaseUrl: normalizedUrl, deviceId: deviceId.trim(), apiKey, mode }); }
    finally { setApiKey(''); setBusy(false); }
  };
  return <View style={styles.form}>
    <Text style={styles.title}>Provision this phone</Text>
    <Text style={styles.help}>Development-only manual provisioning. The key is verified before encrypted device storage and is never shown again.</Text>
    <Field label="API base URL" value={apiBaseUrl} onChangeText={setApiBaseUrl} placeholder="http://192.168.1.100:8001/api/v1" />
    <Field label="Device ID" value={deviceId} onChangeText={setDeviceId} placeholder="front-door-1" />
    <Field label="Device key" value={apiKey} onChangeText={setApiKey} placeholder="Owner-provided key" secureTextEntry />
    <Text style={styles.label}>SCANNER MODE</Text>
    <View style={styles.modeRow}>{(['both', 'check_in', 'check_out'] as ScannerMode[]).map((item) => <ModeButton key={item} label={item.replace('_', ' ')} selected={mode === item} onPress={() => setMode(item)} />)}</View>
    <Pressable accessibilityRole="button" style={styles.primary} onPress={() => void submit()} disabled={busy}><Text style={styles.primaryText}>{busy ? 'VERIFYING…' : 'VERIFY & SAVE'}</Text></Pressable>
  </View>;
}

function Success({ result, onReset }: { result: ScanResult; onReset: () => void }) {
  const presentation = buildSuccessPresentation(result, GYM_TIMEZONE);
  return <View accessibilityLiveRegion="assertive" style={[styles.panel, styles.success]}>
    <Text style={styles.resultKicker}>{presentation.action}</Text>
    <Text style={styles.member}>{presentation.displayName}</Text>
    <Text style={styles.badge}>{presentation.membershipStatus}</Text>
    <Text style={styles.time}>{presentation.occurredAt}</Text>
    <Text style={styles.occupancy}>{presentation.occupancy}</Text>
    <Text style={styles.help}>{presentation.crowdedness}</Text>
    <Pressable accessibilityRole="button" style={styles.primary} onPress={onReset}><Text style={styles.primaryText}>SCAN NEXT</Text></Pressable>
  </View>;
}

function Panel({ title, detail, requestId, action, onPress }: { title: string; detail: string; requestId?: string; action: string; onPress: () => void }) {
  return <View accessibilityLiveRegion="assertive" style={styles.panel}><Text style={styles.title}>{title}</Text><Text style={styles.help}>{detail}</Text>{requestId ? <Text style={styles.request}>Request ID: {requestId}</Text> : null}<Pressable accessibilityRole="button" style={styles.primary} onPress={onPress}><Text style={styles.primaryText}>{action.toUpperCase()}</Text></Pressable></View>;
}

function ModeButton({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ selected }} style={[styles.mode, selected && styles.modeSelected]} onPress={onPress}><Text style={[styles.modeText, selected && styles.modeTextSelected]}>{label.toUpperCase()}</Text></Pressable>;
}

function Field(props: React.ComponentProps<typeof TextInput> & { label: string }) {
  const { label, ...input } = props;
  return <View><Text style={styles.label}>{label.toUpperCase()}</Text><TextInput {...input} accessibilityLabel={input.accessibilityLabel ?? label} autoCapitalize="none" autoCorrect={false} placeholderTextColor="#777" style={styles.input} /></View>;
}

function normalizeError(error: unknown) {
  return error instanceof ScannerApiError ? { code: error.code, message: error.message, requestId: error.requestId } : { code: 'UNKNOWN_ERROR', message: 'The scanner request failed.' };
}

function safeDeviceId(deviceId: string) { return deviceId.length <= 14 ? deviceId : `…${deviceId.slice(-12)}`; }

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0a', paddingHorizontal: 20, paddingTop: 16 },
  brand: { color: '#fff', fontSize: 24, fontWeight: '900', letterSpacing: 1.5 }, orange: { color: ORANGE },
  body: { flex: 1, paddingTop: 18, gap: 16 }, deviceRow: { flexDirection: 'row', alignItems: 'center', gap: 8 }, dot: { width: 9, height: 9, borderRadius: 5 }, muted: { color: '#aaa', fontSize: 13 },
  modeRow: { flexDirection: 'row', gap: 10, flexWrap: 'wrap' }, mode: { minHeight: 50, flexGrow: 1, paddingHorizontal: 14, borderRadius: 14, borderWidth: 1, borderColor: '#333', alignItems: 'center', justifyContent: 'center' }, modeSelected: { backgroundColor: ORANGE, borderColor: ORANGE }, modeText: { color: '#aaa', fontWeight: '800' }, modeTextSelected: { color: '#101010' }, lockedMode: { color: ORANGE, fontWeight: '900', letterSpacing: 1 },
  cameraShell: { flex: 1, minHeight: 360, overflow: 'hidden', borderRadius: 24, borderWidth: 2, borderColor: '#333', alignItems: 'center', justifyContent: 'center' }, target: { width: 240, height: 240, borderRadius: 24, borderWidth: 4, borderColor: ORANGE }, freeze: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(0,0,0,.72)', alignItems: 'center', justifyContent: 'center' }, freezeText: { color: '#fff', fontSize: 24, fontWeight: '900' }, instruction: { color: '#ddd', textAlign: 'center', fontSize: 17, marginBottom: 18 },
  form: { flex: 1, gap: 16, justifyContent: 'center' }, title: { color: '#fff', fontSize: 28, fontWeight: '900' }, help: { color: '#bbb', fontSize: 16, lineHeight: 23, textAlign: 'center' }, label: { color: '#aaa', fontSize: 11, fontWeight: '800', marginBottom: 7, letterSpacing: 1 }, input: { minHeight: 52, borderWidth: 1, borderColor: '#3a3a3a', borderRadius: 13, backgroundColor: '#171717', color: '#fff', paddingHorizontal: 14, fontSize: 16 },
  primary: { minHeight: 54, borderRadius: 14, backgroundColor: ORANGE, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18, marginTop: 8 }, primaryText: { color: '#111', fontWeight: '900', letterSpacing: .8 },
  panel: { flex: 1, borderRadius: 24, backgroundColor: '#171717', padding: 24, alignItems: 'center', justifyContent: 'center', gap: 15 }, success: { borderWidth: 2, borderColor: GREEN }, resultKicker: { color: GREEN, fontSize: 22, fontWeight: '900', letterSpacing: 1.5 }, member: { color: '#fff', fontSize: 34, fontWeight: '900', textAlign: 'center' }, badge: { color: '#0b2119', backgroundColor: GREEN, paddingHorizontal: 14, paddingVertical: 7, borderRadius: 999, fontWeight: '900' }, time: { color: '#ddd', fontSize: 17 }, occupancy: { color: '#fff', fontSize: 46, fontWeight: '900' }, request: { color: '#888', fontSize: 12 },
});
