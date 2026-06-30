import { useQuery, type UseQueryResult } from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// Shared current-user hook.
//
// Wraps `GET /api/me` so the navbar, mobile drawer, and profile page share a
// single cached request. Returns `null` when the user is signed out (401) and
// throws on any other non-OK response.
// ---------------------------------------------------------------------------

export interface LinkedAccounts {
  discord: { linked: true; username: string };
  racetime: { linked: boolean; id: string | null; url: string | null };
  twitch: { linked: boolean; name: string | null };
}

export interface MeData {
  id: string;
  name: string;
  avatar_url: string;
  display_name: string | null;
  linked_accounts: LinkedAccounts;
}

async function fetchMe(): Promise<MeData | null> {
  const r = await fetch('/api/me');
  if (r.status === 401) return null;
  if (!r.ok) throw new Error(`/api/me returned ${r.status}`);
  const body = (await r.json()) as { data: MeData };
  return body.data;
}

export function useMe(): UseQueryResult<MeData | null> {
  return useQuery({ queryKey: ['me'], queryFn: fetchMe });
}
