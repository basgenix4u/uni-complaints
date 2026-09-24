import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowPathIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

function isChunkLoadError(error) {
  const message = `${error?.name || ''} ${error?.message || ''}`;
  return /ChunkLoadError|Loading chunk|dynamically imported module|Importing a module script failed/i.test(message);
}

/**
 * Keeps a failed lazy route from becoming a blank white page.
 *
 * A deployment can leave an already-open tab holding an old Vite manifest
 * while the server has removed the old chunk. One automatic refresh gets the
 * new manifest; other render errors get an explicit recovery screen instead
 * of an unhelpful empty document.
 */
export default class AppErrorBoundary extends React.Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Keep the browser console useful for diagnosis while still giving the
    // person a recovery path in the rendered application.
    console.error('Application render error', error, info);

    if (!isChunkLoadError(error)) return;

    try {
      const key = 'resolve-chunk-reload-attempted';
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, '1');
      window.location.reload();
    } catch {
      // Storage can be unavailable in private or restricted browsing modes.
      // The fallback screen remains usable without it.
    }
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
        <section
          role="alert"
          className="w-full max-w-md rounded-xl border border-line bg-surface p-6 text-center shadow-e2 sm:p-8"
        >
          <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-[#B45309]" aria-hidden="true" />
          <h1 className="mt-4 font-display text-2xl font-semibold text-ink-900">
            This page could not load
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-ink-600">
            The application hit an unexpected error. Try loading the page again. Your saved
            complaint draft is kept on this device.
          </p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="inline-flex min-h-touch items-center justify-center gap-2 rounded-md bg-brand-700 px-4 font-semibold text-white transition-colors hover:bg-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
            >
              <ArrowPathIcon className="h-5 w-5" aria-hidden="true" />
              Reload page
            </button>
            <Link
              to="/"
              className="inline-flex min-h-touch items-center justify-center rounded-md border border-line px-4 font-semibold text-ink-700 transition-colors hover:bg-canvas focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
            >
              Go to home
            </Link>
          </div>
        </section>
      </main>
    );
  }
}
