import { useCallback, useState } from 'react';

/**
 * Whether caps lock is on, judged from the last key event on the field.
 *
 * A password field hides its characters, so this is the one place a
 * stuck caps lock key produces a wrong password with no visible cause.
 * The browser knows; the user cannot see.
 */
export default function useCapsLock() {
  const [capsLock, setCapsLock] = useState(false);

  const onKeyEvent = useCallback((event) => {
    if (typeof event.getModifierState === 'function') {
      setCapsLock(event.getModifierState('CapsLock'));
    }
  }, []);

  // Spread onto the input: both events, so the warning clears when the
  // key is released as well as appearing when it is pressed.
  return [capsLock, { onKeyDown: onKeyEvent, onKeyUp: onKeyEvent }];
}
