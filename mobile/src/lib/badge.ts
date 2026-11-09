// Unread badge text: nothing at 0, "99+" above 99.
export function badgeText(count: number | null | undefined) {
  if (!count || count <= 0) return '';
  return count > 99 ? '99+' : String(count);
}

export function bellLabel(count: number | null | undefined) {
  return count && count > 0 ? `Notifications, ${count} unread` : 'Notifications';
}
