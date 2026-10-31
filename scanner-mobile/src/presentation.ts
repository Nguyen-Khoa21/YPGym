import type { ScanResult } from './types.ts';

export function buildSuccessPresentation(result: ScanResult, timeZone: string) {
  return {
    action: result.action === 'check_in' ? 'CHECKED IN' : 'CHECKED OUT',
    displayName: result.member.display_name,
    membershipStatus: result.member.membership_status.toUpperCase(),
    occurredAt: new Intl.DateTimeFormat('en', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone,
    }).format(new Date(result.occurred_at)),
    occupancy: `${result.occupancy.active_count} / ${result.occupancy.capacity}`,
    crowdedness: `${result.occupancy.status} occupancy`,
  };
}
