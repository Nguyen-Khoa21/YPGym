// Transport shapes mirror the existing FastAPI response schemas; no browser code is imported.
export type User = { id: string; name: string; email: string; phone: string; role: string; tier: string; is_email_verified: boolean };
export type LoginResponse = { access_token: string; expires_at: string; user: User };
export type RegisterResponse = { message: string; user: User };
export type VerifyEmailResponse = { message: string; user: User | null };
export type MemberClass = { id: string; title: string; class_type: string; description: string | null; start_at: string; end_at: string; location: string; capacity: number; remaining_capacity: number; trainer: { display_name: string } | null; member_state: string; waitlist_position: number | null };
export type Booking = { id: string; status: string; can_cancel: boolean; cancellation_cutoff: string; gym_class: MemberClass };
export type Waitlist = { id: string; status: string; position: number; gym_class: MemberClass };
export type Dashboard = {
  member: { id: string; name: string; tier: string };
  membership: { id: string; plan_name: string; status: string; expiry_date: string; days_remaining: number; message: string } | null;
  qr_access: { eligible: boolean; reason: string | null };
  crowdedness: { active_count: number; capacity: number; percentage: number; status: string };
  upcoming_bookings: Booking[]; active_waitlists: Waitlist[]; unread_notification_count: number;
  recent_notifications: Notification[]; active_broadcasts: { id: string; title: string; message: string }[];
};
export type QrToken = { token: string; expires_at: string; membership_status: string };
export type ClassList = { items: MemberClass[]; booking_eligible: boolean; eligibility_reason: string | null };
export type Bookings = { bookings: Booking[]; waitlists: Waitlist[]; cancellation_window_hours: number };
export type Plan = { id: string; name: string; duration_months: number; duration_days: number; final_price: string; discount_percent: string; benefits: string[]; is_active: boolean; tier_availability: string | null };
export type Purchase = { membership: { plan_name: string; expiry_date: string }; payment: { amount: string; status: string }; invoice: { id: string; invoice_number: string } };
export type Invoice = { id: string; invoice_number: string; plan_name: string; amount: string; transaction_date: string; membership_expiry_date: string };
export type Notification = { id: string; title: string; message: string; read_at: string | null; created_at: string; category: string; notification_type: string; action_type: string | null; action_id: string | null };
export type NotificationPage = { items: Notification[]; unread_count: number; page: { page: number; pages: number; total: number } };
export type Preferences = { email_enabled: boolean; in_app_enabled: boolean; expiry_reminders_enabled: boolean; class_reminders_enabled: boolean; broadcasts_enabled: boolean };
export type AttendanceHistory = { items: { id: string; checked_in_at: string; closed_at: string | null; status: string; source: string }[]; distinct_visit_days: string[]; gym_timezone: string };
export type MembershipRequest = { id: string; membership_id: string; request_type: 'freeze' | 'cancellation'; status: string; reason: string; outcome: string | null; decision_reason: string | null; requested_start_date: string | null; requested_end_date: string | null; created_at: string; reviewed_at: string | null };
