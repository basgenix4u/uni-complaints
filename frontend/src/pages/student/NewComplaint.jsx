import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { ArrowLeftIcon, ArrowRightIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select, Textarea } from '../../components/ui/Field';
import Receipt from '../../components/complaints/Receipt';
import { CATEGORY_GROUPS, PRIORITY, categoryLabel } from '../../utils/status';
import { complaintService, errorMessage, fieldErrors } from '../../services/api';
import useAuthStore from '../../stores/authStore';
import useDraft, { loadDraft } from '../../hooks/useDraft';
import useOnline from '../../hooks/useOnline';

const TITLE_MIN = 5;
const BODY_MIN = 20;
const BODY_MAX = 5000;

const STEPS = ['What is it about', 'What happened', 'Check and send'];

export default function NewComplaint() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [step, setStep] = useState(0);
  const [search, setSearch] = useState('');
  // Restored from the draft if one survives — the words are the part a
  // person cannot cheaply produce twice, so they are never the part
  // that is lost to a dropped connection or a locked phone.
  const [form, setForm] = useState(() => ({
    category: '',
    title: '',
    description: '',
    priority: 'medium',
    is_anonymous: false,
    ...loadDraft('complaint', user?.id),
  }));
  const [restored] = useState(() => Boolean(loadDraft('complaint', user?.id)?.description));
  const clearDraft = useDraft('complaint', user?.id, form);
  const online = useOnline();

  const anonymityOffered = Boolean(user?.institution?.allow_anonymous);
  const [errors, setErrors] = useState({});
  const [receipt, setReceipt] = useState(null);

  const set = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const groups = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return CATEGORY_GROUPS;
    return CATEGORY_GROUPS.map((group) => ({
      ...group,
      items: group.items.filter((item) => item.label.toLowerCase().includes(term)),
    })).filter((group) => group.items.length > 0);
  }, [search]);

  const submit = useMutation({
    mutationFn: () => complaintService.create(form),
    onSuccess: (data) => {
      // Only a successful submission clears the draft. A failure keeps
      // every word.
      clearDraft();
      setReceipt(data.complaint);
    },
    onError: (error) => {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { form: errorMessage(error) });
      // Send the user back to the step holding the problem.
      if (fields.title || fields.description) setStep(1);
      else if (fields.category) setStep(0);
    },
  });

  if (receipt) {
    return (
      <div className="px-3 py-6 sm:px-4 sm:py-10">
        <Receipt complaint={receipt} institution={user?.institution} />
      </div>
    );
  }

  const validateStep = () => {
    const found = {};
    if (step === 0 && !form.category) found.category = 'Choose what this is about.';
    if (step === 1) {
      if (form.title.trim().length < TITLE_MIN) {
        found.title = `Give it a short title of at least ${TITLE_MIN} characters.`;
      }
      if (form.description.trim().length < BODY_MIN) {
        found.description = `Add a bit more detail — what happened, and when? (${BODY_MIN} characters minimum)`;
      }
    }
    setErrors(found);
    return Object.keys(found).length === 0;
  };

  const next = () => validateStep() && setStep((current) => current + 1);

  return (
    <div className="mx-auto max-w-2xl px-1 py-3 sm:px-4 sm:py-8">
      <h1 className="font-display text-xl font-semibold tracking-tight sm:text-2xl text-ink-900">
        File a complaint
      </h1>
      <p className="mt-1 text-ink-600">
        Give us the details and we will route it to the right department.
      </p>

      {!online && (
        <p
          role="status"
          className="mt-3 rounded-md px-3 py-2.5 text-sm font-medium sm:mt-4 sm:px-4 sm:py-3"
          style={{
            backgroundColor: 'var(--status-progress-bg)',
            color: 'var(--status-progress-fg)',
          }}
        >
          You are offline. Keep writing — everything here is saved on this device, and you can
          send it when the connection returns.
        </p>
      )}

      {restored && (
        <div
          role="status"
          className="mt-3 flex items-start justify-between gap-2 rounded-md border border-line bg-canvas px-3 py-2.5 text-sm sm:mt-4 sm:gap-3 sm:px-4 sm:py-3"
        >
          <span className="text-ink-700">
            We kept what you wrote last time. Carry on where you stopped, or start over.
          </span>
          <button
            type="button"
            onClick={() => {
              clearDraft();
              setForm({
                category: '',
                title: '',
                description: '',
                priority: 'medium',
                is_anonymous: false,
              });
              setStep(0);
            }}
            className="shrink-0 font-semibold text-brand-700 hover:text-brand-800"
          >
            Start over
          </button>
        </div>
      )}

      <ol className="mt-4 flex gap-2 sm:mt-6" aria-label="Progress">
        {STEPS.map((label, index) => (
          <li key={label} className="flex-1" aria-current={index === step ? 'step' : undefined}>
            <div
              className={`h-1.5 rounded-full ${index <= step ? 'bg-brand-700' : 'bg-line'}`}
              aria-hidden="true"
            />
            <p
              className={`mt-2 text-caption font-semibold ${
                index <= step ? 'text-ink-900' : 'text-ink-500'
              }`}
            >
              {label}
            </p>
          </li>
        ))}
      </ol>

      <div className="mt-4 rounded-lg border border-line bg-surface p-3 shadow-e1 sm:mt-7 sm:p-6">
        {step === 0 && (
          <div className="space-y-4 sm:space-y-5">
            <Input
              label="Find a category"
              placeholder="Try 'transcript' or 'hostel'"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              hint="Or pick from the groups below."
            />

            {errors.category && (
              <p role="alert" className="text-caption font-medium text-[#B91C1C]">
                {errors.category}
              </p>
            )}

            <div className="space-y-4 sm:space-y-5">
              {groups.map((group) => (
                <fieldset key={group.name}>
                  <legend className="mb-2 text-sm font-bold text-ink-900">
                    <span aria-hidden="true">{group.icon}</span> {group.name}
                  </legend>
                  <div className="flex flex-wrap gap-2">
                    {group.items.map((item) => {
                      const selected = form.category === item.value;
                      return (
                        <button
                          key={item.value}
                          type="button"
                          onClick={() => set('category', item.value)}
                          aria-pressed={selected}
                          className={`min-h-touch rounded-md border px-3.5 py-2 text-sm font-medium transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700 ${
                            selected
                              ? 'border-brand-700 bg-brand-50 text-brand-800'
                              : 'border-line bg-surface text-ink-700 hover:border-brand-600'
                          }`}
                        >
                          {item.label}
                        </button>
                      );
                    })}
                  </div>
                </fieldset>
              ))}
              {groups.length === 0 && (
                <p className="text-sm text-ink-500">
                  Nothing matches that. Clear the search to see every category.
                </p>
              )}
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4 sm:space-y-5">
            <Input
              label="Title"
              required
              placeholder="Transcript request not processed"
              value={form.title}
              onChange={(event) => set('title', event.target.value)}
              error={errors.title}
              hint="One line that sums it up."
              maxLength={200}
            />
            <Textarea
              label="What happened"
              required
              rows={7}
              placeholder="Explain what happened, when it started, and anything you have already tried."
              value={form.description}
              onChange={(event) => set('description', event.target.value)}
              error={errors.description}
              hint={`${form.description.length} of ${BODY_MAX} characters. Dates and reference numbers help.`}
              maxLength={BODY_MAX}
            />
            <Select
              label="How urgent is it"
              value={form.priority}
              onChange={(event) => set('priority', event.target.value)}
              hint="Staff may adjust this once they have read it."
            >
              {Object.entries(PRIORITY).map(([value, config]) => (
                <option key={value} value={value}>
                  {config.label} — {config.hint}
                </option>
              ))}
            </Select>

            {anonymityOffered && (
              <div className="rounded-md border border-line bg-canvas p-4">
                <label className="flex items-start gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 shrink-0 rounded border-line"
                    checked={form.is_anonymous}
                    onChange={(event) => set('is_anonymous', event.target.checked)}
                  />
                  <span>
                    <span className="font-bold text-ink-900">Send this without my name</span>
                    <span className="mt-1 block text-ink-700">
                      Staff handling it will not see who you are. You will still get a
                      ticket number and can follow the reply here, but nobody can contact
                      you outside this page, so put everything they need in the details
                      above.
                    </span>
                  </span>
                </label>
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-ink-900">Check this before sending</h2>
            <dl className="divide-y divide-line overflow-hidden rounded-md border border-line text-sm">
              <Summary label="About" value={categoryLabel(form.category)} />
              <Summary label="Title" value={form.title} />
              <Summary label="Urgency" value={PRIORITY[form.priority]?.label} />
              {anonymityOffered && (
                <Summary
                  label="Your name"
                  value={form.is_anonymous ? 'Hidden from staff' : 'Visible to staff'}
                />
              )}
            </dl>
            <div>
              <p className="mb-1.5 text-caption font-bold uppercase tracking-wider text-ink-500">
                What happened
              </p>
              <p className="whitespace-pre-wrap rounded-md border border-line bg-canvas p-3 text-sm leading-relaxed text-ink-700 sm:p-4">
                {form.description}
              </p>
            </div>
            <p className="rounded-md border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-900">
              Once sent you will get a ticket number and a date by which the department must reply.
              You can add files afterwards.
            </p>
            {errors.form && (
              <p role="alert" className="text-caption font-medium text-[#B91C1C]">
                {errors.form}
              </p>
            )}
          </div>
        )}

        <div className="mt-5 flex items-center justify-between gap-2 sm:mt-7 sm:gap-3">
          <Button
            type="button"
            variant="ghost"
            onClick={() => (step === 0 ? navigate(-1) : setStep((current) => current - 1))}
          >
            <ArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
            {step === 0 ? 'Cancel' : 'Back'}
          </Button>

          {step < 2 ? (
            <Button type="button" onClick={next}>
              Continue
              <ArrowRightIcon className="h-4 w-4" aria-hidden="true" />
            </Button>
          ) : (
            <Button
              type="button"
              loading={submit.isPending}
              disabled={!online}
              onClick={() => submit.mutate()}
            >
              {submit.isPending
                ? 'Securing your complaint'
                : online
                  ? 'Send complaint'
                  : 'Offline — draft saved'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function Summary({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 bg-surface px-4 py-3">
      <dt className="text-ink-500">{label}</dt>
      <dd className="text-right font-semibold text-ink-900">{value}</dd>
    </div>
  );
}
