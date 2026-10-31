export type ScannerMode = 'both' | 'check_in' | 'check_out';
export type Action = 'check_in' | 'check_out';
export type Credentials = { apiBaseUrl: string; deviceId: string; apiKey: string; mode: ScannerMode };
export type Occupancy = { active_count: number; capacity: number; percentage: number; status: string; calculated_at: string };
export type ScanResult = {
  code: string;
  message: string;
  session_id: string;
  member_id: string;
  member: { display_name: string; membership_status: string };
  attendance_status: 'active' | 'checked_out';
  action: Action;
  occurred_at: string;
  occupancy: Occupancy;
};
export type ScannerError = { code: string; message: string; requestId?: string };
