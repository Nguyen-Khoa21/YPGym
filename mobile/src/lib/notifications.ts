import type { Notification } from '@/lib/types';

export function notificationTarget(item: Pick<Notification, 'action_type' | 'action_id'>) {
  if (item.action_type === 'class_booking' && item.action_id) {
    return { pathname: '/(member)/bookings' as const, params: { bookingId: item.action_id } };
  }
  return null;
}
