import { useSyncExternalStore } from 'react';

/**
 * Whether the browser believes it has a network.
 *
 * navigator.onLine is optimistic — it reports true on a captive portal
 * or a dead cell — but its false is trustworthy, and false is the case
 * worth warning about: submitting a complaint into a void.
 */
function subscribe(callback) {
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
}

export default function useOnline() {
  return useSyncExternalStore(subscribe, () => navigator.onLine, () => true);
}
