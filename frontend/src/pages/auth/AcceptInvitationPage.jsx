import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Field';
import { errorMessage, invitationService } from '../../services/api';

/**
 * Accepting an invitation to join as staff.
 *
 * The other half of the invitation flow. Without this page every link
 * sent since stage 2 led nowhere, which made the whole feature
 * unusable however correct the API was.
 *
 * The role, unit and institution are shown but never sent back: they
 * come from the invitation on the server, so nobody can accept their way
 * into more access than they were offered.
 */
export default function AcceptInvitationPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token');

  const [state, setState] = useState(token ? 'loading' : 'invalid');
  const [invitation, setInvitation] = useState(null);
  const [message, setMessage] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) return;

    invitationService
      .preview(token)
      .then((data) => {
        setInvitation(data);
        setFullName(data.full_name || '');
        setState('ready');
      })
      .catch((error) => {
        setMessage(errorMessage(error));
        setState('invalid');
      });
  }, [token]);

  const submit = async (event) => {
    event.preventDefault();

    const found = {};
    if (fullName.trim().length < 3) found.full_name = 'Enter your full name.';
    if (password.length < 8) found.password = 'Use at least 8 characters.';
    else if (!/[A-Z]/.test(password)) found.password = 'Include a capital letter.';
    else if (!/[a-z]/.test(password)) found.password = 'Include a small letter.';
    else if (!/\d/.test(password)) found.password = 'Include a number.';
    if (password !== confirm) found.confirm = 'Those two do not match.';

    setErrors(found);
    if (Object.keys(found).length) return;

    setSaving(true);
    try {
      await invitationService.accept({ token, password, full_name: fullName.trim() });
      setState('done');
    } catch (error) {
      setMessage(errorMessage(error));
      setState('invalid');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-10">
      {state === 'loading' && (
        <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-e2">
          <div
            className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-brand-700 border-t-transparent"
            role="status"
            aria-label="Checking the invitation"
          />
        </div>
      )}

      {state === 'invalid' && (
        <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-e2">
          <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-ink-500" aria-hidden="true" />
          <h1 className="mt-3 font-display text-xl font-semibold text-ink-900">
            That invitation cannot be used.
          </h1>
          <p className="mt-1.5 text-ink-600">
            {message ||
              'The link is incomplete. Invitations expire after a fortnight and work only once.'}
          </p>
          <p className="mt-3 text-sm text-ink-600">
            Ask whoever invited you to send a new one.
          </p>
          <Link to="/login" className="mt-5 block">
            <Button variant="secondary" className="w-full">
              Back to sign in
            </Button>
          </Link>
        </div>
      )}

      {state === 'done' && (
        <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-e2">
          <CheckCircleIcon className="mx-auto h-12 w-12 text-brand-700" aria-hidden="true" />
          <h1 className="mt-3 font-display text-xl font-semibold text-ink-900">
            Your account is ready.
          </h1>
          <p className="mt-1.5 text-ink-600">
            Sign in with the password you just chose.
          </p>
          <Button className="mt-5 w-full" onClick={() => navigate('/login')}>
            Sign in
          </Button>
        </div>
      )}

      {state === 'ready' && invitation && (
        <div className="rounded-2xl border border-line bg-surface p-8 shadow-e2">
          <h1 className="font-display text-2xl font-semibold text-ink-900">
            Join {invitation.institution}
          </h1>
          <p className="mt-1.5 text-ink-600">
            You have been invited as{' '}
            <strong className="font-semibold text-ink-900">
              {(invitation.role || '').replace('_', ' ')}
            </strong>
            {invitation.department ? ` in ${invitation.department}` : ''}
            {invitation.faculty ? ` for ${invitation.faculty}` : ''}.
          </p>

          <dl className="mt-5 rounded-lg border border-line bg-canvas px-4 py-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-ink-500">Your sign-in email</dt>
              <dd className="font-semibold text-ink-900">{invitation.email}</dd>
            </div>
          </dl>

          <form className="mt-5 space-y-4" onSubmit={submit}>
            <Input
              label="Your name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              error={errors.full_name}
              required
            />
            <Input
              label="Choose a password"
              type="password"
              hint="At least 8 characters, with a capital, a small letter and a number."
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              error={errors.password}
              required
            />
            <Input
              label="Confirm password"
              type="password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              error={errors.confirm}
              required
            />

            <p className="text-caption text-ink-500">
              Nobody else knows this password, including whoever invited you.
            </p>

            <Button type="submit" className="w-full" loading={saving}>
              Create my account
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}
