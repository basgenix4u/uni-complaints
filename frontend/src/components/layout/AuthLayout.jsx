import { Outlet, Link } from 'react-router-dom';
import { motion } from 'framer-motion';

import Brand from './Brand';

/**
 * The signed-out shell: a photographic panel on the left, the form on
 * the right, joined by a curved seam.
 *
 * The panel used to be a gradient with floating shapes. A photograph of
 * a Nigerian campus says what the product is for in less time than the
 * heading does, so it earns the bytes — but only once they are kept
 * small. The image ships as WebP at three widths and the browser picks
 * one; a twenty-pixel blurred copy is inlined below so the panel has
 * colour on first paint rather than flashing white.
 */

// Inlined rather than fetched: a placeholder that needs its own request
// has missed the moment it exists for.
const PLACEHOLDER = 'data:image/webp;base64,UklGRuoAAABXRUJQVlA4IN4AAABwBQCdASoUABsAPtVaokyoJSMiMAwBABqJbACdMtwhPATlubccM9tD5wUFZ2KoFzsHl33AAP54Vnzp1/hVU7KV59b5xAbz6cFEyFieubQcaduZkyh4CywTTQdGtu8ZYCOn2sanFgB3vrt4eSURCdASJFpieNfFHa1js7SxAtzI+mq24H3u3j8Dkbw6A0hE6pay8z1WSdRdLTUUR23dNwrYphkvA98ahp5dEa6dDU8JLastlS0G/rADd9ztM5xJy9yZ6wMPBczZs1n51aZdYA8NZYvoaobN8Jrm1VMQAAA=';

const PROMISES = [
  ['A ticket, immediately', 'Track it without signing in. Nothing gets lost in an inbox.'],
  ['A named deadline', 'Counted in working hours, and escalated up the chain if it passes.'],
  ['The right office', 'Your complaint is routed on submission. You need not know who handles what.'],
];

function TicketIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M4 8.5A1.5 1.5 0 0 1 5.5 7h13A1.5 1.5 0 0 1 20 8.5v2a2 2 0 0 0 0 4v2a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 16.5v-2a2 2 0 0 0 0-4v-2Z"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path d="M13 8.5v8" stroke="currentColor" strokeWidth="1.6" strokeDasharray="2 2" />
    </svg>
  );
}

function ClockIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <circle cx="12" cy="12" r="8.2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M12 7.6V12l2.8 1.8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function ShieldIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M12 3.6 5.5 6.2v5c0 3.7 2.6 7.1 6.5 8.3 3.9-1.2 6.5-4.6 6.5-8.3v-5L12 3.6Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="m9.3 12 1.9 1.9 3.5-3.6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const ICONS = [TicketIcon, ClockIcon, ShieldIcon];

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen bg-white">
      {/* Photographic panel */}
      <div className="relative hidden w-1/2 shrink-0 overflow-hidden bg-brand-900 lg:block">
        <img
          src="/img/campus-1024.webp"
          srcSet="/img/campus-640.webp 640w, /img/campus-1024.webp 1024w, /img/campus-1536.webp 1536w"
          sizes="50vw"
          alt=""
          aria-hidden="true"
          // Above the fold on every signed-out page, so it is fetched
          // eagerly and at high priority rather than lazily.
          loading="eager"
          fetchPriority="high"
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
          style={{ backgroundImage: `url(${PLACEHOLDER})`, backgroundSize: 'cover' }}
        />

        {/* Green wash. The photograph is bright, and the copy on top of
            it has to stay legible without hiding the campus behind it. */}
        <div
          className="absolute inset-0"
          style={{
            background:
              'linear-gradient(105deg, rgba(4,49,36,0.94) 0%, rgba(6,63,45,0.82) 38%, rgba(6,63,45,0.34) 66%, rgba(6,63,45,0.16) 100%)',
          }}
        />

        <div className="relative z-10 flex h-full flex-col justify-between px-12 py-12 xl:px-16">
          <Link to="/" className="inline-flex w-fit items-center gap-3">
            <Brand className="h-14 w-14" />
            <span>
              <span className="block font-display text-2xl font-bold text-white">Resolve</span>
              <span className="block text-sm text-white/70">Complaints that reach someone</span>
            </span>
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
          >
            <h2 className="font-display text-4xl font-bold leading-[1.1] text-white xl:text-5xl">
              Streamline Your
              <br />
              <span className="text-accent-300">University Experience</span>
            </h2>
            <p className="mt-5 max-w-md text-lg leading-relaxed text-white/85">
              Submit complaints, track requests, and get faster resolutions. Your voice matters,
              and we&rsquo;re here to help.
            </p>

            {/* What the product promises. The figures that were here
                before -- 10K+ resolved, 98% satisfaction, a testimonial
                from a Dean -- were invented. Nobody has used this yet,
                and inventing evidence on a complaints system is
                precisely the dishonesty it exists to address. */}
            <ul className="mt-10 space-y-5">
              {PROMISES.map(([title, detail], index) => {
                const Icon = ICONS[index];
                return (
                  <li key={title} className="flex gap-4">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600/90 ring-1 ring-white/20">
                      <Icon className="h-5 w-5 text-white" />
                    </span>
                    <span className="pt-0.5">
                      <span className="block font-semibold text-white">{title}</span>
                      <span className="mt-0.5 block max-w-sm text-sm leading-snug text-white/75">
                        {detail}
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </motion.div>

          <p className="font-display text-2xl italic leading-tight text-white">
            Better Campus.
            <br />
            <span className="text-accent-300">Together.</span>
            <svg
              viewBox="0 0 150 8"
              className="mt-1 h-2 w-36 text-accent-400"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M2 5.5c28-3.4 92-4.6 146-1.8"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
              />
            </svg>
          </p>
        </div>

        {/* The seam. A curve cut out of the panel's right edge in the
            page background colour, so the form appears to sit in front
            of the photograph rather than beside it. */}
        <svg
          className="absolute inset-y-0 right-0 hidden h-full w-16 text-white lg:block"
          viewBox="0 0 64 1000"
          preserveAspectRatio="none"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M64 0H30c0 180 34 200 34 340v320c0 140-34 160-34 340h34V0Z" />
        </svg>
      </div>

      {/* Form */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-12 sm:px-12">
        {/* Corner flourishes, matching the panel. Decorative only. */}
        <svg
          className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 text-brand-800"
          viewBox="0 0 200 200"
          fill="none"
          aria-hidden="true"
        >
          <path d="M200 0v120C200 54 146 0 80 0h120Z" fill="currentColor" />
          <path
            d="M18 2c58 14 104 60 118 118"
            stroke="var(--accent-400, #E0A82E)"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
        <svg
          className="pointer-events-none absolute -bottom-12 -left-12 h-56 w-56 text-brand-800"
          viewBox="0 0 200 200"
          fill="none"
          aria-hidden="true"
        >
          <path d="M0 200V80c0 66 54 120 120 120H0Z" fill="currentColor" />
          <path
            d="M182 198c-58-14-104-60-118-118"
            stroke="var(--accent-400, #E0A82E)"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
        <svg
          className="pointer-events-none absolute bottom-6 right-6 h-28 w-28 text-brand-100"
          viewBox="0 0 64 64"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M32 16 8 26l24 10 24-10-24-10Z"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinejoin="round"
          />
          <path d="M18 31v11c0 3.9 6.3 7 14 7s14-3.1 14-7V31" stroke="currentColor" strokeWidth="2.4" />
          <path d="M56 26v13" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        </svg>

        <div className="relative z-10 w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <Link to="/" className="flex items-center gap-3">
              <Brand className="h-12 w-12" />
              <span>
                <span className="block font-display text-xl font-bold text-ink-900">Resolve</span>
                <span className="block text-xs text-ink-500">Complaints that reach someone</span>
              </span>
            </Link>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <Outlet />
          </motion.div>
        </div>
      </div>
    </div>
  );
}
