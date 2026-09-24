import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { EnvelopeIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Field';
import InstitutionPicker from '../../components/auth/InstitutionPicker';
import useAuthStore from '../../stores/authStore';
import { authService, errorMessage } from '../../services/api';

/**
 * Registering as a student.
 *
 * Three changes from the form this replaces, all of which were lies the
 * old one told:
 *
 * 1. It never sent an institution at all, so registration could not
 *    succeed against the real API.
 * 2. It offered ten hardcoded faculties to every university. Faculty and
 *    department now come from the institution's own register, or are
 *    left out, rather than being guessed from a fixed list.
 * 3. A matriculation number is asked for only where it will actually be
 *    checked. Demanding one an institution cannot verify is an obstacle
 *    that proves nothing.
 */
export default function RegisterPage() {
  const navigate = useNavigate();
  const { register: registerUser, isLoading } = useAuthStore();

  const [institution, setInstitution] = useState(null);
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    matric_number: '',
    phone: '',
    password: '',
    confirm_password: '',
  });
  const [errors, setErrors] = useState({});
  const [done, setDone] = useState(null);

  const set = (field) => (event) => {
    setForm({ ...form, [field]: event.target.value });
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const needsMatric = institution?.verification_mode === 'register';

  const validate = () => {
    const found = {};

    if (form.full_name.trim().length < 3) found.full_name = 'Enter your full name.';
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) {
      found.email = 'Enter a valid email address.';
    }
    if (needsMatric && !form.matric_number.trim()) {
      found.matric_number = 'Enter your matric number so we can check the student register.';
    }
    if (form.matric_number.trim() &&
        !/^[A-Za-z]{2,5}[\s\-_/]+[A-Za-z]{2,5}[\s\-_/]+\d{2,4}[\s\-_/]+\d{3,6}$/.test(
          form.matric_number.trim(),
        )) {
      found.matric_number = `Check the format, for example ${
        institution?.matric_example || 'ENG/COE/21/013'
      }.`;
    }
    if (form.password.length < 8) found.password = 'Use at least 8 characters.';
    else if (!/[A-Z]/.test(form.password)) found.password = 'Include a capital letter.';
    else if (!/[a-z]/.test(form.password)) found.password = 'Include a small letter.';
    else if (!/\d/.test(form.password)) found.password = 'Include a number.';
    if (form.password !== form.confirm_password) {
      found.confirm_password = 'Those two do not match.';
    }

    setErrors(found);
    return Object.keys(found).length === 0;
  };

  const onSubmit = async (event) => {
    event.preventDefault();

    if (!institution) {
      setErrors({ institution: 'Choose your institution first.' });
      return;
    }
    if (!validate()) return;

    const { confirm_password: _ignored, ...rest } = form;
    const result = await registerUser({
      ...rest,
      matric_number: rest.matric_number.trim() || undefined,
      institution: institution.slug,
    });

    if (result.success) {
      // Straight to the confirmation step rather than the dashboard: the
      // account cannot do anything until the address is verified, and
      // dropping them somewhere they are blocked would be confusing.
      setDone(form.email);
      return;
    }

    setErrors(result.errors || {});
    toast.error(result.error || 'We could not create the account.');
  };

  if (done) {
    return <ConfirmationStep email={done} onWrongEmail={() => setDone(null)} />;
  }

  return (
    <div>
      <div className="mb-6 text-center sm:mb-8">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-2 font-display text-2xl font-bold text-ink-900 sm:text-3xl"
        >
          Create an account
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-ink-600"
        >
          So your complaint reaches someone who can act on it.
        </motion.p>
      </div>

      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        onSubmit={onSubmit}
        className="space-y-4"
      >
        <InstitutionPicker value={institution} onChange={setInstitution} />
        {errors.institution && (
          <p role="alert" className="text-caption font-medium text-[#B91C1C]">
            {errors.institution}
          </p>
        )}

        {institution && (
          <>
            <Input
              label="Full name"
              placeholder="As it appears on your student record"
              value={form.full_name}
              onChange={set('full_name')}
              error={errors.full_name}
              required
            />

            <Input
              label="Email address"
              type="email"
              placeholder="you@example.com"
              hint="Any address you actually read. It does not have to be a university one."
              value={form.email}
              onChange={set('email')}
              error={errors.email}
              required
            />

            {needsMatric && (
              <Input
                label="Matric number"
                placeholder={institution.matric_example || 'ENG/COE/21/013'}
                hint="We check this against your institution's student register."
                value={form.matric_number}
                onChange={set('matric_number')}
                error={errors.matric_number}
                required
              />
            )}

            <Input
              label="Phone number"
              type="tel"
              placeholder="08012345678"
              hint="Optional. Used only to text you if a complaint is escalated."
              value={form.phone}
              onChange={set('phone')}
              error={errors.phone}
            />

            <Input
              label="Password"
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={set('password')}
              error={errors.password}
              required
            />
            <PasswordChecklist password={form.password} />

            <Input
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              value={form.confirm_password}
              onChange={set('confirm_password')}
              error={errors.confirm_password}
              required
            />

            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                required
                className="mt-1 h-4 w-4 rounded border-line text-brand-700 focus:outline-2 focus:outline-offset-2 focus:outline-brand-700"
              />
              <span className="text-sm text-ink-600">
                I agree to the{' '}
                <Link to="/privacy" className="font-medium text-brand-700 hover:underline">
                  privacy policy
                </Link>
                .
              </span>
            </label>

            <Button type="submit" size="lg" loading={isLoading} className="mt-2 w-full">
              Create account
            </Button>
          </>
        )}
      </motion.form>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="mt-5 text-center sm:mt-6 text-ink-600"
      >
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          Sign in
        </Link>
      </motion.p>
    </div>
  );
}

/**
 * The wall after registering.
 *
 * This is the step most likely to lose the person: the link is in an
 * inbox they may have misspelt, on a provider that may be slow, filed
 * under spam. A dead end here costs the account. So the screen can send
 * the link again — on a cooldown, because pressing it repeatedly only
 * queues duplicates — and can go back if the address itself was wrong.
 */
function ConfirmationStep({ email, onWrongEmail }) {
  const [cooldown, setCooldown] = useState(0);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timer = setInterval(() => setCooldown((current) => current - 1), 1000);
    return () => clearInterval(timer);
  }, [cooldown > 0]);

  const resend = async () => {
    setSending(true);
    try {
      const result = await authService.resendVerification(email);
      toast.success(result?.message || 'If that address needs confirming, a new link is on its way.');
      setCooldown(60);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="text-center">
      <EnvelopeIcon className="mx-auto h-12 w-12 text-brand-700" aria-hidden="true" />
      <h1 className="mt-3 font-display text-xl font-bold text-ink-900 sm:text-2xl">Check your email.</h1>
      <p className="mx-auto mt-2 max-w-sm text-ink-600">
        We sent a confirmation link to <strong>{email}</strong>. Open it to finish setting up your
        account. It may take a minute, and it is worth checking the spam folder.
      </p>

      <div className="mt-6 flex flex-col items-center gap-3">
        <Button variant="secondary" onClick={resend} loading={sending} disabled={cooldown > 0}>
          {cooldown > 0 ? `Send it again (${cooldown}s)` : 'Send it again'}
        </Button>
        <button
          type="button"
          onClick={onWrongEmail}
          className="text-sm font-medium text-brand-700 hover:text-brand-800"
        >
          Wrong email address? Go back and change it.
        </button>
        <Link to="/login" className="text-sm text-ink-500 hover:text-ink-700">
          Back to sign in
        </Link>
      </div>
    </div>
  );
}


/**
 * The password rules, as live ticks rather than an error after the
 * fact. The rules do not change; what changes is when the person finds
 * out — while typing, not after a rejected submit on paid data.
 */
const PASSWORD_RULES = [
  ['At least 8 characters', (value) => value.length >= 8],
  ['A capital letter', (value) => /[A-Z]/.test(value)],
  ['A small letter', (value) => /[a-z]/.test(value)],
  ['A number', (value) => /\d/.test(value)],
];

function PasswordChecklist({ password }) {
  if (!password) return null;
  return (
    <ul className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1" aria-label="Password requirements">
      {PASSWORD_RULES.map(([label, passes]) => {
        const ok = passes(password);
        return (
          <li
            key={label}
            className={`flex items-center gap-1.5 text-caption ${
              ok ? 'text-brand-700' : 'text-ink-500'
            }`}
          >
            <span aria-hidden="true">{ok ? '\u2713' : '\u00B7'}</span>
            {label}
            <span className="sr-only">{ok ? ' \u2014 met' : ' \u2014 not yet met'}</span>
          </li>
        );
      })}
    </ul>
  );
}
