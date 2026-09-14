export type PageInfo = { page: number; page_size: number; total: number; pages: number };

export type MembershipRecord = {
  id: string;
  plan_id: string;
  plan_name: string;
  status: string;
  start_date: string;
  expiry_date: string;
  frozen_from: string | null;
  frozen_until: string | null;
};

export type AdminMember = {
  id: string;
  name: string;
  email: string;
  phone: string;
  role: string;
  tier: string;
  is_email_verified: boolean;
  membership: MembershipRecord | null;
  created_at: string;
};

export type AdminMemberPage = {
  items: AdminMember[];
  page: PageInfo;
  summary: { total: number; active: number; expiring_soon: number; frozen: number; expired_or_inactive: number };
};

export type MembershipRequest = {
  id: string;
  membership_id: string;
  request_type: "freeze" | "cancellation";
  status: string;
  reason: string;
  outcome: string | null;
  decision_reason: string | null;
  requested_start_date: string | null;
  requested_end_date: string | null;
  created_at: string;
  reviewed_at: string | null;
};

export type MembershipApproval = MembershipRequest & {
  user_id: string;
  user_name: string;
  user_email: string;
};

export type MembershipApprovalPage = { items: MembershipApproval[]; page: PageInfo };

export type AuditItem = {
  id: string;
  action: string;
  actor_user_id: string | null;
  actor_name: string | null;
  target_user_id: string | null;
  target_name: string | null;
  entity_type: string;
  entity_id: string | null;
  reason: string | null;
  outcome: string | null;
  summary: string;
  created_at: string;
};

export type AdminMemberDetail = {
  profile: { id: string; name: string; email: string; phone: string; role: string; tier: string; is_email_verified: boolean };
  memberships: MembershipRecord[];
  payments: { id: string; plan_name: string; amount: string; discount_amount: string; status: string; reference: string; created_at: string }[];
  invoices: { id: string; invoice_number: string; plan_name: string; amount: string; transaction_date: string }[];
  attendance_summary: { total_visits: number; active_sessions: number; last_check_in_at: string | null };
  attendance_history: AttendanceSession[];
  booking_summary: { total: number; upcoming: number; waitlisted: number };
  membership_requests: MembershipRequest[];
  audit_logs: AuditItem[];
};

export type BillingPayment = {
  payment_id: string;
  user_id: string;
  member_name: string;
  member_email: string;
  member_tier: string;
  plan_name: string;
  amount: string;
  discount_amount: string;
  status: string;
  created_at: string;
};

export type BillingInvoice = {
  invoice_id: string;
  user_id: string;
  member_name: string;
  member_email: string;
  invoice_number: string;
  plan_name: string;
  amount: string;
  transaction_date: string;
};

export type BillingPage<T> = { items: T[]; page: PageInfo; total_amount: string };
export type AuditPage = { items: AuditItem[]; page: PageInfo };

export type ConfigurationItem = { key: string; value: number; description: string | null; updated_at: string };

export type NotificationPreference = {
  email_enabled: boolean;
  in_app_enabled: boolean;
  expiry_reminders_enabled: boolean;
  broadcasts_enabled: boolean;
};

export type NotificationItem = {
  id: string;
  category: string;
  notification_type: string;
  title: string;
  message: string;
  channel: string;
  delivery_state: string;
  read_at: string | null;
  created_at: string;
};

export type NotificationPage = { items: NotificationItem[]; page: PageInfo; unread_count: number };

export type Broadcast = {
  id: string;
  audience: string;
  title: string;
  message: string;
  starts_at: string;
  ends_at: string | null;
  is_active: boolean;
  creator_id: string;
  created_at: string;
  updated_at: string;
};

export type Crowdedness = {
  active_count: number;
  capacity: number;
  percentage: number;
  status: string;
  calculated_at: string;
};

export type AttendanceEvent = { id: string; event_type: string; event_at: string; source: string; device_id: string | null };

export type AttendanceSession = {
  id: string;
  user_id: string;
  member_name: string | null;
  member_email: string | null;
  checked_in_at: string;
  closed_at: string | null;
  status: string;
  source: string;
  device_id: string | null;
  manual_close_reason: string | null;
  events: AttendanceEvent[];
};

export type AttendancePage = { items: AttendanceSession[]; page: PageInfo };

export type QrToken = { token: string; issued_at: string; expires_at: string; ttl_seconds: number; membership_status: string };

export type PeakHours = {
  cells: { weekday: number; weekday_label: string; hour: number; visits: number }[];
  occupancy: Crowdedness;
  visits_today: number;
  busiest_hour: string | null;
  date_from: string;
  date_to: string;
};

export type AnalyticsSummary = {
  date_from: string;
  date_to: string;
  generated_at: string;
  cache_hit: boolean;
  cache_ttl_seconds: number;
  membership_trends: {
    period: string;
    active: number;
    expiring_soon: number;
    frozen: number;
    expired: number;
    cancelled: number;
    revoked: number;
    pending_verification: number;
    total: number;
  }[];
  class_popularity: {
    class_type: string;
    class_count: number;
    bookings: number;
    unique_members: number;
    capacity: number;
    utilization_percent: number;
  }[];
  attendance: {
    check_ins: number;
    unique_members: number;
    average_visit_minutes: number | null;
    busiest_slot: string | null;
    current_occupancy: Crowdedness;
  };
  revenue: { successful_payments: number; gross_amount: string; discounts: string };
};

export type TrainerClassSummary = {
  id: string;
  title: string;
  class_type: string;
  start_at: string;
  end_at: string;
  location: string;
};

export type Trainer = {
  id: string;
  display_name: string;
  bio: string | null;
  specialty: string | null;
  availability_summary: string | null;
  is_active: boolean;
  upcoming_classes: TrainerClassSummary[];
  user_id?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type GymClass = {
  id: string;
  title: string;
  class_type: string;
  description: string | null;
  start_at: string;
  end_at: string;
  capacity: number;
  status: string;
  trainer_id: string | null;
  trainer_name: string | null;
  location: string;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type ClassPage = { items: GymClass[]; page: PageInfo; scheduled_count: number; cancelled_count: number };

export type MemberClass = {
  id: string;
  title: string;
  class_type: string;
  description: string | null;
  start_at: string;
  end_at: string;
  capacity: number;
  status: string;
  location: string;
  confirmed_booking_count: number;
  remaining_capacity: number;
  trainer: Trainer | null;
  member_booking_id: string | null;
  member_booking_status: string | null;
  member_waitlist_status: string | null;
  waitlist_position: number | null;
  member_state: "available" | "booked" | "full" | "waitlisted" | "cancelled" | "ineligible";
};

export type MemberClassList = {
  items: MemberClass[];
  booking_eligible: boolean;
  eligibility_status: string;
  eligibility_reason: string | null;
};

export type ClassBooking = {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  cancellation_cutoff: string;
  can_cancel: boolean;
  gym_class: MemberClass;
};

export type ClassWaitlist = {
  id: string;
  status: string;
  position: number;
  created_at: string;
  updated_at: string;
  gym_class: MemberClass;
};

export type MemberBookings = {
  bookings: ClassBooking[];
  waitlists: ClassWaitlist[];
  cancellation_window_hours: number;
};

export type MemberDashboardPayload = {
  member: { id: string; name: string; tier: string };
  membership: {
    id: string;
    plan_name: string;
    status: string;
    start_date: string;
    expiry_date: string;
    days_remaining: number;
    message: string;
  } | null;
  qr_access: { eligible: boolean; reason: string | null; target: string };
  crowdedness: Crowdedness;
  upcoming_bookings: ClassBooking[];
  active_waitlists: ClassWaitlist[];
  unread_notification_count: number;
  recent_notifications: NotificationItem[];
  active_broadcasts: Broadcast[];
  quick_actions: { key: string; label: string; target: string; enabled: boolean; reason: string | null }[];
};
