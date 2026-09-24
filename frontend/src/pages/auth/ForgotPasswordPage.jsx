import { useState } from 'react';
import { Link } from 'react-router-dom';
import { EnvelopeIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Field';
import { authService, errorMessage } from '../../services/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event) => {
    event.preventDefault();
    if (!email.trim()) {
      setError('Enter the email address on your account.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      await authService.forgotPassword(email.trim());
      setSent(true);
    } catch (requestError) {
      setError(errorMessage(requestError, 'We could not start that reset. Try again shortly.'));
    } finally {
      setBusy(false);
    }
  };

  if (sent) {
    return (
      <div className="w-full">
        <span
          className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-brand-50"
          aria-hidden="true"
        >
          <EnvelopeIcon className="h-7 w-7 text-brand-700" />
        </span>
        <h1 className="text-center font-display text-2xl font-semibold text-ink-900">
          Check your email
        </h1>
        {/* Worded so it never confirms whether an account exists. */}
        <p className="mx-auto mt-2 max-w-sm text-center text-ink-600">
          If that address belongs to an account, a reset link is on its way. It expires in an
          hour.
        </p>
        <p className="mt-6 text-center text-sm text-ink-500">
          Nothing arrived? Check your spam folder, or{' '}
          <button
            type="button"
            onClick={() => setSent(false)}
            className="font-semibold text-brand-700 hover:underline"
          >
            try another address
          </button>
          .
        </p>
        <Link to="/login" className="mt-6 block text-center sm:mt-8 text-sm font-semibold text-brand-700 hover:underline">
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="w-full space-y-4 sm:space-y-5">
      <div>
        <h1 className="font-display text-xl font-semibold tracking-tight sm:text-2xl text-ink-900">
          Forgotten your password
        </h1>
        <p className="mt-1.5 text-ink-600">
          Enter the email on your account and we will send a link to set a new one.
        </p>
      </div>

      <Input
        label="Email address"
        type="email"
        required
        autoComplete="email"
        placeholder="you@institution.edu.ng"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={error}
      />

      <Button type="submit" className="w-full" loading={busy}>
        Send the reset link
      </Button>

      <p className="text-center text-sm text-ink-500">
        Remembered it?{' '}
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
