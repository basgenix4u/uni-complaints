import { useState } from 'react';
import { ArrowDownTrayIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Field';
import { errorMessage, privacyService } from '../../services/api';
import useAuthStore from '../../stores/authStore';

export default function PrivacyPage() {
  const { user, logout } = useAuthStore();

  const [downloading, setDownloading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [erasing, setErasing] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const isStudent = user?.role === 'student';

  const download = async () => {
    setDownloading(true);
    setError('');
    try {
      await privacyService.downloadMyData();
      setNotice('Your data has been downloaded.');
    } catch (downloadError) {
      setError(errorMessage(downloadError, 'We could not build that file. Try again shortly.'));
    } finally {
      setDownloading(false);
    }
  };

  const erase = async () => {
    setErasing(true);
    setError('');
    try {
      await privacyService.eraseMyAccount(password, confirm);
      // Nothing is left to sign in to, so the session ends here.
      logout();
      window.location.href = '/login';
    } catch (eraseError) {
      setError(errorMessage(eraseError, 'We could not complete that.'));
    } finally {
      setErasing(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-1 py-3 sm:px-4 sm:py-8">
      <h1 className="font-display text-xl font-semibold tracking-tight sm:text-2xl text-ink-900">
        Your data
      </h1>
      <p className="mt-1 text-ink-600">
        What we hold about you, and what you can do with it.
      </p>

      {notice && (
        <p
          role="status"
          className="mt-4 rounded-md sm:mt-5 px-4 py-3 text-sm font-medium"
          style={{ backgroundColor: 'var(--status-resolved-bg)', color: 'var(--status-resolved-fg)' }}
        >
          {notice}
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-md sm:mt-5 px-4 py-3 text-sm font-medium"
          style={{ backgroundColor: 'var(--status-declined-bg)', color: 'var(--status-declined-fg)' }}
        >
          {error}
        </p>
      )}

      <section className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:mt-6 sm:p-6">
        <h2 className="text-sm font-bold text-ink-900">Take a copy</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-ink-600">
          Download everything held about you: your account, every complaint you filed, the
          replies you received, and the files you attached. It arrives as a JSON file you can
          keep or hand to someone else.
        </p>
        <Button variant="secondary" className="mt-4" loading={downloading} onClick={download}>
          <ArrowDownTrayIcon className="h-5 w-5" aria-hidden="true" />
          Download my data
        </Button>
      </section>

      <section className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:mt-5 sm:p-6">
        <h2 className="text-sm font-bold text-ink-900">What we keep, and for how long</h2>
        <dl className="mt-3 space-y-2.5 text-sm">
          <Row
            label="Why we hold it"
            value="To receive your complaint, route it to the right department and show you what was decided."
          />
          <Row
            label="Who can see it"
            value="You, and the staff handling your complaint. Never another student, and never another institution."
          />
          <Row
            label="How long"
            value="Until your institution's retention period ends, or until you ask us to erase it."
          />
        </dl>
      </section>

      {isStudent && (
        <section
          className="mt-4 rounded-lg border p-4 sm:mt-5 sm:p-6"
          style={{ borderColor: '#FECACA', backgroundColor: 'var(--status-declined-bg)' }}
        >
          <h2
            className="flex items-center gap-2 text-sm font-bold"
            style={{ color: 'var(--status-declined-fg)' }}
          >
            <ExclamationTriangleIcon className="h-5 w-5" aria-hidden="true" />
            Erase my data
          </h2>
          <p
            className="mt-2 text-sm leading-relaxed"
            style={{ color: 'var(--status-declined-fg)' }}
          >
            This removes your name, email, matric number, phone, the files you uploaded and
            everything you wrote. It cannot be undone and you will not be able to sign in again.
          </p>
          <p
            className="mt-2 text-sm leading-relaxed"
            style={{ color: 'var(--status-declined-fg)' }}
          >
            Complaints you filed stay as anonymous records, because they are also the
            institution&apos;s account of what it decided. Nothing in them will point back to you.
          </p>

          {!confirming ? (
            <Button variant="danger" className="mt-4" onClick={() => setConfirming(true)}>
              Erase my data
            </Button>
          ) : (
            <div className="mt-4 space-y-3 rounded-md border border-line bg-surface p-3 sm:space-y-4 sm:p-4">
              <Input
                label="Your password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                hint="Confirms it is you, not someone using your unlocked device."
              />
              <Input
                label="Type ERASE to confirm"
                required
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                className="font-mono"
              />
              <div className="flex flex-wrap justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setConfirming(false);
                    setPassword('');
                    setConfirm('');
                    setError('');
                  }}
                >
                  Keep my account
                </Button>
                <Button
                  variant="danger"
                  loading={erasing}
                  disabled={!password || confirm.trim().toUpperCase() !== 'ERASE'}
                  onClick={erase}
                >
                  Erase permanently
                </Button>
              </div>
            </div>
          )}
        </section>
      )}

      {!isStudent && (
        <section className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:mt-5 sm:p-6">
          <h2 className="text-sm font-bold text-ink-900">Erasing a staff account</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-ink-600">
            Staff accounts are erased by an administrator, so that open complaints can be handed
            over first. Ask your institution administrator.
          </p>
        </section>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div>
      <dt className="text-caption font-bold uppercase tracking-wider text-ink-500">{label}</dt>
      <dd className="mt-0.5 text-ink-700">{value}</dd>
    </div>
  );
}
