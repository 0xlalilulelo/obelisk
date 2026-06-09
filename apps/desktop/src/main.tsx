import { ClerkProvider } from '@clerk/clerk-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import { ConfigNotice } from './components/ConfigNotice';
import './index.css';
import { config } from './lib/config';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const root = createRoot(document.getElementById('root')!);

root.render(
  <StrictMode>
    {config.clerkPublishableKey ? (
      <ClerkProvider publishableKey={config.clerkPublishableKey} afterSignOutUrl="/">
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ClerkProvider>
    ) : (
      <ConfigNotice />
    )}
  </StrictMode>,
);
