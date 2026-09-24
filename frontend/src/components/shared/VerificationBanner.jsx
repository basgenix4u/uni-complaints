import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { EnvelopeIcon } from '@heroicons/react/24/outline';

import Button from '../ui/Button';
import { authService, errorMessage } from '../../services/api';
import useAuthStore from '../../stores/authStore';

/**
 * Tells a student why they cannot file yet, and what to do about it.
 *
 * Verification gates filing rather than signing in, which means somebody
 * can be inside the application and still blocked. Without this they
 * would only discover that at the end of writing a complaint, which is
 * the worst possible moment.
 */
export default function VerificationBanner() {
  const { user, isAuthenticated } = useAuthStore();
  const [sent, setSent] = useState('');

  const { data } = useQuery({
    queryKey: ['verification-status'],
    queryFn: () => authService.verificationStatus(),
    enabled: Boolean(isAuthenticated && user && user.role === 'student'),
  });

  if (!data || data.can_file) return null;

  const resend = async () => {
    try {
      const result = await authService.resendVerification(data.email);
      setSent(result?.message || 'A new link is on its way.');
    } catch (error) {
      setSent(errorMessage(error));
    }
  };

  return (
    <div
      role="status"
      className="verification-banner flex flex-wrap items-center gap-2 border-b sm:gap-3 border-[#FCD34D] bg-[#FFFBEB] px-3 py-2.5 sm:px-4 sm:py-3 text-sm"
    >
      <EnvelopeIcon className="h-5 w-5 shrink-0 text-[#B45309]" aria-hidden="true" />
      <p className="min-w-0 flex-1 text-[#78350F]">{data.reason}</p>

      {!data.is_verified &&
        (sent ? (
          <span className="font-medium text-[#78350F]">{sent}</span>
        ) : (
          <Button size="sm" variant="secondary" onClick={resend}>
            Send it again
          </Button>
        ))}
    </div>
  );
}
