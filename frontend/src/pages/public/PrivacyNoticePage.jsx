import { Link } from 'react-router-dom';

export default function PrivacyNoticePage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-16">
      <Link to="/register" className="text-sm font-semibold text-brand-700 hover:underline">
        Back to registration
      </Link>

      <header className="mt-5">
        <p className="text-caption font-bold uppercase tracking-wider text-ink-500">Resolve</p>
        <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight text-ink-900">
          Privacy notice
        </h1>
        <p className="mt-2 max-w-2xl text-ink-600">
          Resolve helps institutions receive, route and resolve complaints. This notice explains
          what the service uses your information for before you create an account.
        </p>
      </header>

      <div className="mt-8 space-y-5">
        <Section title="What we collect">
          We collect the details you provide when you register or file a complaint, such as your
          name, contact details, student information, complaint details and any files you attach.
        </Section>
        <Section title="Why we use it">
          We use that information to create your account, route your complaint to the right
          institution team, show you replies and deadlines, and keep an accurate record of what
          the institution decided.
        </Section>
        <Section title="Who can see it">
          Your information is limited to you and the authorised people handling your complaint at
          your institution. It is not shared with another student or another institution through
          the application.
        </Section>
        <Section title="Your choices">
          After signing in, you can download the information held about you. You can also ask for
          your account to be erased from the Your data page. The institution may retain an
          anonymised record where it is needed to document how a complaint was handled.
        </Section>
        <Section title="Questions">
          If you have a question about how your institution uses the service, contact the
          institution administrator before submitting sensitive information.
        </Section>
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          to="/register"
          className="inline-flex min-h-touch items-center justify-center rounded-md bg-brand-700 px-4 font-semibold text-white hover:bg-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
        >
          Create an account
        </Link>
        <Link
          to="/login"
          className="inline-flex min-h-touch items-center justify-center rounded-md border border-line px-4 font-semibold text-ink-700 hover:bg-canvas focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}

function Section({ title, children }) {
  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-e1 sm:p-5">
      <h2 className="text-sm font-bold text-ink-900">{title}</h2>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{children}</p>
    </section>
  );
}
