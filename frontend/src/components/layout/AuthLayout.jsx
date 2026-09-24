import { Link, Outlet } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ClockIcon,
  ShieldCheckIcon,
  TicketIcon,
} from '@heroicons/react/24/outline';

import hero1600 from '../../assets/auth/hero-1600.webp';
import hero1000 from '../../assets/auth/hero-1000.webp';
import hero640 from '../../assets/auth/hero-640.webp';

// A twenty pixel wide copy of the photograph, inlined so it needs no
// request. It is painted behind the real image and blurred up to cover
// it, so the panel is never an empty rectangle on a slow connection.
const BLUR = 'data:image/webp;base64,UklGRjYBAABXRUJQVlA4ICoBAAAQBwCdASoUABsAPt1cpUyopSOiMAgBEBuJbACdMuIjmJvz4B4AmgHXGPrm5n9LsHMg954spBUg0enu3wce65EkAAD+ovG9wyKvMx1Gh63pkvNOi6G7WQV8Xrvm9Skg6zFQ9FwTL2E3Ytwb1sBCRuMpNTvgq+Hd1df8pLNvCy/3h23lbmQYUncxATULTlu7qsBi87tHuzee8UsOiWf6jna361m7rATFAsXXspMa0Ev37D2RXfX5lWgPlOvpRgs+96Wg03BWJHLYlmFR9eFAwlE/E8Zm6rmzh/NpDrUSSTvg+x4beKZdp3e+1Au1HKs8pU4DDA8HZ5GT4bQVY1LV4t1iLjbsXIfH/0pVJx7+RDYPculE4Sgt3XnarCjEuoQ08Ft1pTKbQ+BwXgAA';

const PROMISES = [
  [TicketIcon, 'A ticket, immediately', 'Track it without signing in. Nothing gets lost in an inbox.'],
  [ClockIcon, 'A named deadline', 'Counted in working hours, and escalated up the chain if it passes.'],
  [ShieldCheckIcon, 'The right office', 'Your complaint is routed on submission. You need not know who handles what.'],
];

function Wordmark({ tone = 'light' }) {
  const dark = tone === 'dark';
  return (
    <Link to="/" className="inline-flex items-center gap-3">
      <span
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-xl font-bold shadow-e2 ${
          dark ? 'bg-brand-700 text-white' : 'bg-white text-brand-700'
        }`}
        aria-hidden="true"
      >
        U
      </span>
      <span>
        <span
          className={`block font-display text-2xl font-bold leading-tight ${
            dark ? 'text-ink-900' : 'text-white'
          }`}
        >
          Resolve
        </span>
        <span className={`block text-caption ${dark ? 'text-ink-500' : 'text-white/80'}`}>
          Complaints that reach someone
        </span>
      </span>
    </Link>
  );
}

export default function AuthLayout() {
  const still = useReducedMotion();
  const rise = still
    ? {}
    : { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 } };

  return (
    <div className="flex min-h-screen bg-surface">
      {/* Left: the photograph, with the promise over it. Hidden below
          lg, where it would push the form off the first screen. */}
      <div className="relative hidden w-1/2 shrink-0 overflow-hidden lg:block">
        <img
          src={BLUR}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 h-full w-full scale-110 object-cover blur-xl"
        />
        {/* A picture element rather than a plain img: hiding the panel
            with CSS below lg does not stop the browser fetching the
            photograph, so a phone was downloading a hundred kilobytes for
            something it never displays. A source with a media query is
            the only thing that actually prevents the request. */}
        <picture>
          <source
            media="(min-width: 1024px)"
            type="image/webp"
            srcSet={`${hero640} 640w, ${hero1000} 1000w, ${hero1600} 1600w`}
            sizes="50vw"
          />
          {/* The fallback is the smallest variant: it is only ever used
              by a browser without picture support, and below lg the panel
              is hidden anyway. */}
          <img
            src={hero640}
            alt=""
            aria-hidden="true"
            // Eager and high priority: on a large screen this is the
            // largest element on the page, so deferring it is what a
            // visitor would perceive as the page being slow.
            loading="eager"
            fetchPriority="high"
            decoding="async"
            className="absolute inset-0 h-full w-full object-cover"
          />
        </picture>

        {/* The wash. Measured off the supplied design rather than
            guessed: the sample tints only the left side, where the copy
            sits, and lets the photograph stand untouched where the
            student sits. A full-panel tint made the whole image look
            green; this one is gone by two-thirds across. */}
        <div
          className="absolute inset-0"
          style={{
            background:
              'linear-gradient(to right, rgba(2,22,11,0.94) 0%, rgba(3,36,20,0.80) 28%, rgba(5,52,33,0.40) 45%, rgba(6,63,45,0.10) 60%, rgba(6,63,45,0) 70%)',
          }}
        />
        {/* A shallow floor of shade so the sign-off stays readable over
            bright foliage at the bottom, matching the sample's base. */}
        <div
          className="absolute inset-x-0 bottom-0 h-40"
          style={{
            background: 'linear-gradient(to top, rgba(2,22,11,0.55), rgba(2,22,11,0))',
          }}
        />

        <div className="relative z-20 flex h-full flex-col justify-between p-10 xl:p-14">
          <Wordmark />

          <motion.div {...rise} transition={{ duration: 0.45 }}>
            <h2 className="font-display text-4xl font-bold leading-[1.1] text-white xl:text-5xl">
              Streamline Your
              <br />
              <span className="text-[#F4B740]">University Experience</span>
            </h2>
            <p className="mt-5 max-w-md text-white/90">
              Submit complaints, track requests, and get faster resolutions. Your voice
              matters, and we&rsquo;re here to help.
            </p>

            <ul className="mt-9 space-y-4">
              {PROMISES.map(([Icon, title, detail]) => (
                <li key={title} className="flex gap-3.5">
                  <span
                    aria-hidden="true"
                    className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-700/90 ring-1 ring-white/20"
                  >
                    <Icon className="h-5 w-5 text-white" />
                  </span>
                  <span className="min-w-0">
                    <span className="block font-semibold text-white">{title}</span>
                    <span className="block text-sm leading-snug text-white/80">{detail}</span>
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>

          <p className="font-display text-xl italic leading-tight text-white">
            Better Campus.
            <br />
            <span className="text-[#F4B740]">Together.</span>
            <span
              aria-hidden="true"
              className="mt-1.5 block h-0.5 w-28 rounded-full bg-[#F4B740]"
            />
          </p>
        </div>
      </div>

      {/* Right: the form, on a panel whose inner edge curves over the
          photograph. */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden bg-surface px-4 py-8 sm:px-10 sm:py-12">
        {/* The curved edge, drawn only where there is a photograph to
            curve over. */}
        <Corners />

        <div className="relative z-10 w-full max-w-md">
          <div className="mb-8">
            <Wordmark tone="dark" />
          </div>

          <motion.div {...rise} transition={{ duration: 0.4 }}>
            <Outlet />
          </motion.div>
        </div>
      </div>
    </div>
  );
}

/**
 * The flourishes on the form panel, matched to the supplied design by
 * measurement rather than memory:
 *
 * - top-right: a solid green quarter-round tucked into the corner,
 *   spanning roughly the top 17% of the panel's height and the last 8%
 *   of its width, with a detached gold arc sweeping just outside its
 *   inner edge;
 * - bottom-left: a green fin rising from the seam along the bottom,
 *   with its own gold arc above it;
 * - bottom-right: the outlined mortarboard watermark.
 *
 * The dark corner green matches the sample's sampled value (#0C5645
 * territory) rather than the brighter action green.
 */
function Corners() {
  return (
    <>
      {/* Top-right quarter-round with gold arc outside it. */}
      <svg
        aria-hidden="true"
        viewBox="0 0 260 160"
        className="pointer-events-none absolute right-0 top-0 h-32 w-52 sm:h-36 sm:w-60"
        preserveAspectRatio="xMaxYMin meet"
      >
        <path d="M260 0 H96 C150 10 216 52 232 160 H260 Z" fill="#0C5645" />
        <path
          d="M76 0 C136 12 202 58 220 160"
          fill="none"
          stroke="#E0A82E"
          strokeWidth="4"
          strokeLinecap="round"
        />
      </svg>

      {/* Bottom-left fin against the seam, gold arc above it. */}
      <svg
        aria-hidden="true"
        viewBox="0 0 200 140"
        className="pointer-events-none absolute bottom-0 left-0 h-28 w-40 sm:h-32 sm:w-48"
        preserveAspectRatio="xMinYMax meet"
      >
        <path d="M0 140 V28 C10 92 62 128 118 140 Z" fill="#0C5645" />
        <path
          d="M4 8 C18 76 74 118 140 132"
          fill="none"
          stroke="#E0A82E"
          strokeWidth="4"
          strokeLinecap="round"
        />
      </svg>

      {/* The mortarboard watermark. */}
      <svg
        aria-hidden="true"
        viewBox="0 0 64 64"
        className="pointer-events-none absolute bottom-12 right-14 h-16 w-16"
        fill="none"
        stroke="rgba(11,107,87,0.13)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M32 12 L58 24 L32 36 L6 24 Z" />
        <path d="M16 29 V43 C16 43 22 50 32 50 C42 50 48 43 48 43 V29" />
        <path d="M58 24 V40" />
      </svg>
    </>
  );
}
