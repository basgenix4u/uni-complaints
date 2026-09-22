import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  BuildingLibraryIcon,
  CheckCircleIcon,
  ClockIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

import Button from '../ui/Button';
import { Input } from '../ui/Field';
import { directoryService, errorMessage } from '../../services/api';
import { institutionTypeLabel } from '../../utils/institutionTypes';

/**
 * Choosing where you study.
 *
 * The old form asked a student to type an institution slug, which nobody
 * outside the project knows, and answered a wrong guess with "we could
 * not find that institution" — a dead end that helped nobody.
 *
 * Institutions that have not signed up are shown too, and deliberately
 * so: "we know your university but they are not using this yet" is a
 * different answer from "never heard of it", and it leads somewhere.
 */
export default function InstitutionPicker({ value, onChange }) {
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [asking, setAsking] = useState(null);
  const [asked, setAsked] = useState(false);
  const [email, setEmail] = useState('');
  const [problem, setProblem] = useState('');
  const [active, setActive] = useState(0);
  // Reset during render rather than in an effect: the highlight belongs
  // to a particular set of results, and carrying it into the next set
  // would point at whatever happens to sit in that position.
  const [activeFor, setActiveFor] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(timer);
  }, [query]);



  const { data, isFetching } = useQuery({
    queryKey: ['directory', debounced],
    queryFn: () => directoryService.search({ q: debounced }),
  });

  const interest = useMutation({
    mutationFn: (payload) => directoryService.registerInterest(payload),
    onSuccess: () => {
      setAsked(true);
      setProblem('');
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const institutions = data?.institutions ?? [];

  if (activeFor !== debounced) {
    setActiveFor(debounced);
    setActive(0);
  }

  const choose = (institution) =>
    institution.is_onboarded
      ? onChange(institution)
      : setAsking({ name: institution.name, slug: institution.slug });

  // With several hundred institutions the list is the main interface, so
  // it has to be reachable without a mouse. Enter is intercepted because
  // this renders inside the registration form and would otherwise submit
  // it half-filled.
  const onSearchKeyDown = (event) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!institutions.length) return;
      setActive((current) => {
        const next = event.key === 'ArrowDown' ? current + 1 : current - 1;
        return (next + institutions.length) % institutions.length;
      });
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (institutions[active]) choose(institutions[active]);
    }
  };

  if (value) {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-brand-200 bg-brand-50 p-4">
        <CheckCircleIcon className="h-5 w-5 shrink-0 text-brand-700" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink-900">{value.name}</p>
          {value.state && <p className="text-caption text-ink-600">{value.state}</p>}
        </div>
        <Button size="sm" variant="ghost" onClick={() => onChange(null)}>
          Change
        </Button>
      </div>
    );
  }

  if (asked) {
    return (
      <div className="rounded-lg border border-line bg-surface p-5 text-center">
        <ClockIcon className="mx-auto h-8 w-8 text-brand-700" aria-hidden="true" />
        <p className="mt-2 font-semibold text-ink-900">Thank you. We have noted it.</p>
        <p className="mt-1 text-sm text-ink-600">
          We will email you as soon as {asking?.name || 'your institution'} is using Resolve. The
          more students who ask, the sooner that tends to happen.
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="mt-3"
          onClick={() => {
            setAsked(false);
            setAsking(null);
          }}
        >
          Look for another institution
        </Button>
      </div>
    );
  }

  const submitInterest = () => {
    // Validated here rather than by the browser: this is not a form
    // element, for the reason given below, so `required` would do nothing.
    if (!asking.name?.trim()) {
      setProblem('Enter the name of your institution.');
      return;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setProblem('Enter a valid email address so we can tell you when it is ready.');
      return;
    }

    setProblem('');
    interest.mutate({
      institution_name: asking.name,
      institution_slug: asking.slug,
      email,
    });
  };

  if (asking) {
    // Deliberately not a <form>. This component renders inside the
    // registration form, and a nested form is invalid HTML: the browser
    // discards the inner one, so the button would submit the outer form
    // and try to create an account instead.
    return (
      <div
        className="space-y-3 rounded-lg border border-line bg-surface p-5"
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault();
            submitInterest();
          }
        }}
      >
        <p className="font-semibold text-ink-900">
          {asking.slug ? `${asking.name} is not using Resolve yet.` : 'Tell us where you study.'}
        </p>
        <p className="text-sm text-ink-600">
          Leave your email and we will let you know the moment they are.
        </p>

        {!asking.slug && (
          <Input
            label="Your institution"
            value={asking.name}
            onChange={(event) => setAsking({ ...asking, name: event.target.value })}
            placeholder="Bayero University Kano"
          />
        )}

        <Input
          label="Your email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
        />

        {problem && (
          <p role="alert" className="text-caption font-medium text-[#B91C1C]">
            {problem}
          </p>
        )}

        <div className="flex gap-2">
          <Button type="button" size="sm" loading={interest.isPending} onClick={submitInterest}>
            Tell me when it is ready
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setAsking(null)}>
            Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <Input
        label="Your institution"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Start typing, for example Bayero or BUK"
        autoComplete="off"
        onKeyDown={onSearchKeyDown}
        role="combobox"
        aria-expanded={institutions.length > 0}
        aria-controls="institution-results"
      />

      <div aria-live="polite">
        {isFetching && <p className="text-caption text-ink-500">Searching…</p>}

        {!isFetching && institutions.length === 0 && debounced && (
          <div className="rounded-lg border border-line bg-surface p-4 text-sm">
            <p className="text-ink-700">
              We have no record of an institution matching “{debounced}”.
            </p>
            <Button
              size="sm"
              variant="secondary"
              className="mt-3"
              onClick={() => setAsking({ name: debounced, slug: null })}
            >
              Ask us to add it
            </Button>
          </div>
        )}

        {institutions.length > 0 && (
          <ul id="institution-results" className="max-h-72 space-y-2 overflow-y-auto">
            {institutions.map((institution, index) => (
              <li key={institution.id}>
                <button
                  type="button"
                  onClick={() => choose(institution)}
                  onMouseEnter={() => setActive(index)}
                  aria-selected={index === active}
                  className={`flex w-full items-center gap-3 rounded-lg border bg-surface p-3.5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700 ${
                    index === active ? 'border-brand-600' : 'border-line hover:border-brand-600'
                  }`}
                >
                  <BuildingLibraryIcon
                    className="h-5 w-5 shrink-0 text-ink-500"
                    aria-hidden="true"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-ink-900">
                      {institution.name}
                    </span>
                    {/* Several institutions share a name and differ only
                        by state or type, so the subtitle is what makes
                        the right one pickable. */}
                    <span className="block truncate text-caption text-ink-500">
                      {[
                        institution.short_name,
                        institution.state,
                        institutionTypeLabel(institution.type),
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  </span>
                  {institution.is_onboarded ? (
                    <span className="shrink-0 rounded-full bg-brand-50 px-2.5 py-0.5 text-caption font-semibold text-brand-800">
                      Available
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-full bg-canvas px-2.5 py-0.5 text-caption font-semibold text-ink-600">
                      Not yet
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
