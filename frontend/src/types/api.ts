export type UserRole = "member" | "staff" | "manager" | "admin" | "pt";

export type User = {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  tier: "normal" | "advance" | "vip";
  is_email_verified: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: User;
};

export type MembershipPlan = {
  id: string;
  name: string;
  duration_months: number;
  duration_days: number;
  base_price: string;
  discount_percent: string;
  final_price: string;
  is_active: boolean;
  tier_availability: string | null;
  benefits: string[];
};

export type AttendanceBenefitQuote = {
  gym_timezone: string;
  period_start: string;
  period_end: string;
  attended_days: number;
  period_days: number;
  attendance_percentage: string;
  threshold_percentage: string;
  benefit_discount_percent: string;
  attendance_qualified: boolean;
  available: boolean;
  status: "eligible" | "not_qualified" | "not_renewal" | "pending" | "consumed";
  pricing: {
    rule: "better_of";
    consumption_rule: "first_successful_renewal";
    transaction_kind: "purchase" | "renewal";
    base_price: string;
    plan_discount_percent: string;
    attendance_discount_percent: string;
    applied_discount_percent: string;
    attendance_benefit_selected: boolean;
    discount_amount: string;
    final_amount: string;
  };
};

export type PaymentHistoryItem = {
  id: string;
  product_type: "membership" | "class_booking";
  product_name: string;
  class_booking_id: string | null;
  plan_name: string;
  amount: string;
  discount_amount: string;
  status: string;
  mock_reference: string;
  provider: string;
  reference: string;
  paid_at: string | null;
  expires_at: string | null;
  created_at: string;
  discount_details: AttendanceBenefitQuote | null;
};

export type VNPayCreateResponse = {
  transaction_id: string;
  txn_ref: string;
  payment_url: string;
  expires_at: string;
};

export type PaymentStatus = {
  id: string;
  product_type: "membership" | "class_booking";
  membership_plan_id: string | null;
  class_booking_id: string | null;
  product_name: string;
  plan_name: string | null;
  provider: string;
  txn_ref: string;
  status: "pending" | "paid" | "failed" | "cancelled" | "expired" | "paid_review";
  amount_vnd: number;
  currency: "VND";
  membership_status: string | null;
  membership_start_date: string | null;
  membership_expiry_date: string | null;
  booking_status: string | null;
  refund_status: string | null;
  class_start_at: string | null;
  class_end_at: string | null;
  invoice_id: string | null;
  invoice_download_url: string | null;
  created_at: string;
  paid_at: string | null;
  expires_at: string | null;
  discount_details: AttendanceBenefitQuote | null;
};

export type InvoiceHistoryItem = {
  id: string;
  invoice_number: string;
  plan_name: string;
  product_type: "membership" | "class_booking";
  product_name: string;
  class_booking_id: string | null;
  amount: string;
  discount_amount: string;
  transaction_date: string;
  membership_start_date: string | null;
  membership_expiry_date: string | null;
  service_start_at: string | null;
  service_end_at: string | null;
  download_url: string;
  discount_details: AttendanceBenefitQuote | null;
};

export type PurchaseResponse = {
  message: string;
  membership: {
    id: string;
    plan_id: string;
    plan_name: string;
    status: string;
    start_date: string;
    expiry_date: string;
  };
  payment: {
    id: string;
    amount: string;
    discount_amount: string;
    status: string;
    mock_reference: string;
    created_at: string;
  };
  invoice: InvoiceHistoryItem;
};
