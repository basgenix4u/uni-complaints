import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircleIcon, ClockIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Field';
import { authService, errorMessage } from '../../services/api';

/**
 * Confirming an email address from the link.
 *
 * A failed confirmation is the more important case to get right: the
 * link may be old, already used, or for an address that has since
 * changed. Each of those needs a way forward rather than a dead end, so
 * this screen always offers to send a new one.
 */
export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get('token');

  const [state, setState] = useState(token ? 'checking' : 'missing');
  const [message, setMessage] = useState('');
  const [approval, setApproval] = useState(null);
  const [email, setEmail] = useState('');
  const [resent, setResent] = useState('');

  // React runs effects twice in development, and a verification token is
  // single use, so the second call would report an already-used link.
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;

    authService
      .verifyEmail(token)
      .then((data) => {
        setApproval(data.approval_status);
        setState('done');
      })
      .catch((error) => {
        setMessage(errorMessage(error));
        setState('failed');
      });
  }, [token]);

  const resend = async (event) => {
    event.preventDefault();
    try {
      const data = await authService.resendVerification(email);
      setResent(data?.message || 'If that address needs confirming, a new link is on its way.');
    } catch (error) {
      setResent(errorMessage(error));
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-10">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-e2">
        {state === 'checking' && (
          <>
            <div
              className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-brand-700 border-t-transparent"
              role="status"
              aria-label="Confirming"
            />
            <h1 className="mt-4 font-display text-xl font-semibold text-ink-900">
              Confirming your address…
            </h1>
          </>
        )}

        {state === 'done' && approval !== 'pending' && (
          <>
            <CheckCircleIcon className="mx-auto h-12 w-12 text-brand-700" aria-hidden="true" />
            <h1 className="mt-3 font-display text-xl font-semibold text-ink-900">
              That is confirmed.
            </h1>
            <p className="mt-1.5 text-ink-600">
              Your address is verified and you can file a complaint now.
            </p>
            <Link to="/login" className="mt-5 block">
              <Button className="w-full">Sign in</Button>
            </Link>
          </>
        )}

        {state === 'done' && approval === 'pending' && (
          <>
            <ClockIcon className="mx-auto h-12 w-12 text-brand-700" aria-hidden="true" />
            <h1 className="mt-3 font-display text-xl font-semibold text-ink-900">
              Address confirmed.
            </h1>
            <p className="mt-1.5 text-ink-600">
              Your institution is now checking your registration against their student register.
              We will email you as soon as that is done.
            </p>
            <Link to="/login" className="mt-5 block">
              <Button variant="secondary" className="w-full">
                Sign in
              </Button>
            </Link>
          </>
        )}

        {(state === 'failed' || state === 'missing') && (
          <>
            <ExclamationTriangleIcon
              className="mx-auto h-12 w-12 text-ink-500"
              aria-hidden="true"
            />
            <h1 className="mt-3 font-display text-xl font-semibold text-ink-900">
              That link did not work.
            </h1>
            <p className="mt-1.5 text-ink-600">
              {state === 'missing'
                ? 'The link is incomplete. Use the one from the email, or ask for a new one.'
                : message}
            </p>

            <form className="mt-5 space-y-3 text-left" onSubmit={resend}>
              <Input
                label="Your email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
              <Button type="submit" className="w-full">
                Send me a new link
              </Button>
            </form>

            {resent && (
              <p aria-live="polite" className="mt-3 text-sm font-medium text-brand-800">
                {resent}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
