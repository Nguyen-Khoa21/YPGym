import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 15_000 } } });

const sharedQueryRoots = new Set(['health', 'plans']);
const membershipQueryRoots = ['dashboard', 'profile', 'qr', 'invoices', 'billing', 'plans', 'membership'] as const;

export function clearMemberQueryData(client: QueryClient = queryClient) {
  client.removeQueries({ predicate: (query) => !sharedQueryRoots.has(String(query.queryKey[0])) });
}

export async function refreshMembershipQueryData(client: QueryClient = queryClient) {
  await Promise.all(membershipQueryRoots.map((root) => client.invalidateQueries({ queryKey: [root], refetchType: 'all' })));
}
