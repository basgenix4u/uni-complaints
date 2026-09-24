import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircleIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Field';
import { authService, errorMessage, fieldErrors } from '../../services/api';

const RULES = [
  { label: 'At least 8 characters', test: (value) => value.length >= 8 },
  { label: 'A capital letter', test: (value) => /[A-Z]/.test(value) },
  { label: 'A small letter', test: (value) => /[a-z]/.test(value) },
  { label: 'A number', test: (value) => /\d/.test(value) },
];

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState({});
  const [done, setDone] = useState(false);

  // The same rules the server applies, shown as they are met rather than
  // as a failure after submitting.
  const checks = useMemo(() => RULES.map((rule) => ({ ...rule, met: rule.test(password) })), [password]);
  const satisfied = checks.every((check) => check.met);

  const submit = async (event) => {
    event.preventDefault();

    if (password !== confirm) {
      setErrors({ confirm: 'Both entries need to match.' });
      return;
    }

    setBusy(true);
    setErrors({});
    try {
      await authService.resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate('/login'), 2500);
    } catch (resetError) {
      const fields = fieldErrors(resetError);
      setErrors(Object.keys(fields).length ? fields : { form: errorMessage(resetError) });
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="w-full text-center">
        <h1 className="font-display text-2xl font-semibold text-ink-900">
          That link is incomplete
        </h1>
        <p className="mx-auto mt-2 max-w-sm text-ink-600">
          Open the link from the email exactly as it was sent, or ask for a new one.
        </p>
        <Link to="/forgot-password" className="mt-6 inline-block">
          <Button>Ask for a new link</Button>
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="w-full text-center">
        <span
          className="mx-auto mb-5 flex h-14 w-14 animate-pop items-center justify-center rounded-full bg-brand-700"
          aria-hidden="true"
        >
          <CheckCircleIcon className="h-8 w-8 text-white" />
        </span>
        <h1 className="font-display text-2xl font-semibold text-ink-900">Password changed</h1>
        <p className="mt-2 text-ink-600">Taking you to sign in.</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="w-full space-y-4 sm:space-y-5">
      <div>
        <h1 className="font-display text-xl font-semibold tracking-tight sm:text-2xl text-ink-900">
          Choose a new password
        </h1>
        <p className="mt-1.5 text-ink-600">Pick something you have not used here before.</p>
      </div>

      {errors.form && (
        <p
          role="alert"
          className="rounded-md px-4 py-3 text-sm font-medium"
          style={{ backgroundColor: 'var(--status-declined-bg)', color: 'var(--status-declined-fg)' }}
        >
          {errors.form}
        </p>
      )}

      <Input
        label="New password"
        type="password"
        required
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={errors.password}
      />

      <ul className="space-y-1.5" aria-label="Password requirements">
        {checks.map((check) => (
          <li
            key={check.label}
            className={`flex items-center gap-2 text-caption ${
              check.met ? 'text-[#046C4E]' : 'text-ink-500'
            }`}
          >
            <span aria-hidden="true">{check.met ? '✓' : '○'}</span>
            {check.label}
            <span className="sr-only">{check.met ? ' met' : ' not yet met'}</span>
          </li>
        ))}
      </ul>

      <Input
        label="Type it again"
        type="password"
        required
        autoComplete="new-password"
        value={confirm}
        onChange={(event) => setConfirm(event.target.value)}
        error={errors.confirm}
      />

      <Button type="submit" className="w-full" loading={busy} disabled={!satisfied}>
        Save the new password
      </Button>
    </form>
  );
}
