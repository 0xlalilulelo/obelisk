import { createClient, type ObeliskClient } from '@obelisk/api-client';
import { useAuth } from '@clerk/clerk-react';
import { useMemo } from 'react';

import { config } from './config';

/** A memoized API client bound to the current Clerk session token. */
export function useApi(): ObeliskClient {
  const { getToken } = useAuth();
  return useMemo(
    () => createClient({ baseUrl: config.apiBaseUrl, getToken: () => getToken() }),
    [getToken],
  );
}
