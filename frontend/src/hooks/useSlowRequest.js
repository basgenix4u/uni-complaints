import { useEffect, useRef, useState } from 'react';

/**
 * Escalating reassurance while a request runs.
 *
 * The API sleeps on the free tier and takes thirty to fifty seconds to
 * wake, so the first sign-in of the day looks exactly like a broken
 * site. Nothing about the request is wrong; the silence is. After a few
 * seconds the button starts explaining what is actually happening.
 */
const STAGES = [
  [4, 'Still working…'],
  [10, 'Waking the server — the first request of the day can take up to a minute.'],
  [30, 'Nearly there. The server is starting up; please leave this page open.'],
];

export default function useSlowRequest(active) {
  const [message, setMessage] = useState('');
  const timers = useRef([]);

  // Timers are external to React, so an effect is the right tool; the
  // reset to an empty message happens in the timers' cleanup rather
  // than synchronously in the effect body.
  useEffect(() => {
    if (!active) return undefined;
    timers.current = STAGES.map(([seconds, text]) =>
      setTimeout(() => setMessage(text), seconds * 1000),
    );
    return () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
      setMessage('');
    };
  }, [active]);

  return active ? message : '';
}
