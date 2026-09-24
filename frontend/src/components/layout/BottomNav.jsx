import { NavLink } from 'react-router-dom';
import {
  BellIcon,
  DocumentTextIcon,
  HomeIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline';
import {
  BellIcon as BellSolid,
  DocumentTextIcon as DocumentSolid,
  HomeIcon as HomeSolid,
  PlusCircleIcon as PlusSolid,
} from '@heroicons/react/24/solid';

/**
 * The student's phone navigation.
 *
 * Students are phone-first, and a hamburger hides the whole product
 * behind a tap. The four destinations that matter live in a thumb-reach
 * bar instead; everything else (profile, privacy) stays in the drawer,
 * which remains available. Staff keep the sidebar: triage is desk work.
 */
const ITEMS = [
  { name: 'Home', href: '/student/dashboard', icon: HomeIcon, active: HomeSolid },
  { name: 'Complaints', href: '/student/complaints', icon: DocumentTextIcon, active: DocumentSolid, end: true },
  { name: 'New', href: '/student/complaints/new', icon: PlusCircleIcon, active: PlusSolid },
  { name: 'Alerts', href: '/student/notifications', icon: BellIcon, active: BellSolid },
];

export default function BottomNav() {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] shadow-e3 backdrop-blur-xl lg:hidden"
    >
      <ul className="grid grid-cols-4">
        {ITEMS.map(({ name, href, icon: Icon, active: ActiveIcon, end }) => (
          <li key={href}>
            <NavLink
              to={href}
              end={end}
              className={({ isActive }) =>
                `flex min-h-12 flex-col items-center justify-center gap-0 text-[11px] font-medium leading-tight sm:min-h-14 sm:gap-0.5 sm:text-caption ${
                  isActive ? 'text-brand-700' : 'text-ink-500'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive ? (
                    <ActiveIcon className="h-5 w-5 sm:h-6 sm:w-6" aria-hidden="true" />
                  ) : (
                    <Icon className="h-5 w-5 sm:h-6 sm:w-6" aria-hidden="true" />
                  )}
                  {name}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
