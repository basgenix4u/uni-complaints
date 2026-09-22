import { useCallback, useEffect, useRef } from 'react';

/**
 * Keep a form's state in localStorage until it is deliberately cleared.
 *
 * The complaint form is where this matters most: someone writes two
 * thousand characters about something that took courage to write at
 * all, the network blinks or the phone locks, and the words are gone.
 * That person rarely writes them twice. Persistence costs nothing and
 * is invisible until the day it saves the only copy.
 *
 * Storage is per user, so a shared or lab computer does not surface one
 * person's half-written complaint to the next. The draft is removed on
 * successful submission and after a deliberate discard; it is never
 * synced anywhere.
 */
const PREFIX = 'resolve.draft.';

function storageKey(name, userId) {
  return `${PREFIX}${name}.${userId || 'anon'}`;
}

export function loadDraft(name, userId) {
  try {
    const raw = localStorage.getItem(storageKey(name, userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    // Corrupt or blocked storage is the same as no draft.
    return null;
  }
}

export default function useDraft(name, userId, value) {
  const key = storageKey(name, userId);
  const skip = useRef(false);

  // Written on every change, debounced one tick behind the keystroke.
  // localStorage is synchronous, so the debounce keeps it off the
  // typing hot path on slow phones.
  useEffect(() => {
    if (skip.current) {
      // Exactly one write is skipped: the state change that emptied the
      // form after a clear. Anything typed after that is a new draft
      // and must be kept again.
      skip.current = false;
      return undefined;
    }
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch {
        // Quota or private mode: the draft simply is not kept.
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [key, value]);

  const clear = useCallback(() => {
    skip.current = true;
    try {
      localStorage.removeItem(key);
    } catch {
      /* nothing to do */
    }
  }, [key]);

  return clear;
}
