export type UserRole = "member" | "staff" | "manager" | "admin" | "pt";

export type User = {
  id: string;
  name: string;
  email: string;
  phone: string;
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

export type PaymentHistoryItem = {
  id: string;
  plan_name: string;
  amount: string;
  discount_amount: string;
  status: string;
  mock_reference: string;
  created_at: string;
};

export type InvoiceHistoryItem = {
  id: string;
  invoice_number: string;
  plan_name: string;
  amount: string;
  discount_amount: string;
  transaction_date: string;
  membership_start_date: string;
  membership_expiry_date: string;
  download_url: string;
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
