import { useEffect, useRef, useState } from 'react';

/**
 * A live countdown from a 429 response.
 *
 * A limit that reports "too many attempts" and nothing else invites the
 * exact behaviour it exists to stop: trying again immediately. A clock
 * that visibly runs down is calmer, and it tells the truth — the server
 * said precisely how long, in the Retry-After header.
 */
export default function useRetryAfter() {
  const [secondsLeft, setSecondsLeft] = useState(0);
  const timer = useRef(null);

  useEffect(() => () => clearInterval(timer.current), []);

  const start = (error) => {
    const header = error?.response?.headers?.['retry-after'];
    const seconds = Number.parseInt(header, 10);
    if (!Number.isFinite(seconds) || seconds <= 0) return false;

    clearInterval(timer.current);
    setSecondsLeft(seconds);
    timer.current = setInterval(() => {
      setSecondsLeft((current) => {
        if (current <= 1) {
          clearInterval(timer.current);
          return 0;
        }
        return current - 1;
      });
    }, 1000);
    return true;
  };

  const label =
    secondsLeft > 0
      ? `${Math.floor(secondsLeft / 60)}:${String(secondsLeft % 60).padStart(2, '0')}`
      : '';

  return { blocked: secondsLeft > 0, label, start };
}
