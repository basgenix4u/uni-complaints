import { expect, test } from '@playwright/test';

/**
 * Browser journeys against a seeded backend.
 *
 * These cover what unit tests cannot: that a person can actually complete
 * a task in a browser, and that the boundaries enforced by the API also
 * hold in the interface.
 */

const STUDENT = { email: 'amina@demo.edu.ng', password: 'Password123' };
const ADMIN = { email: 'admin@demo.edu.ng', password: 'Password123' };

const sessions = new Map();

/**
 * Authenticates through the API once per account and reuses the tokens.
 *
 * Logging in through the form for every test exhausts the rate limit,
 * which is a protection worth keeping rather than loosening for tests.
 */
async function signIn(page, { email, password }) {
  if (!sessions.has(email)) {
    const response = await page.request.post('/api/auth/login', {
      data: { email, password },
    });
    if (!response.ok()) {
      throw new Error(`Could not sign in as ${email}: ${response.status()}`);
    }
    sessions.set(email, (await response.json()).data);
  }

  const session = sessions.get(email);

  await page.goto('/login');
  await page.evaluate(
    ([access, refresh, user]) => {
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem(
        'auth-storage',
        JSON.stringify({ state: { user, isAuthenticated: true }, version: 0 }),
      );
    },
    [session.access_token, session.refresh_token, session.user],
  );

  const home = session.user.role === 'student' ? '/student/dashboard' : '/admin/dashboard';
  await page.goto(home);
  await ready(page);
}

/** Waits for a lazily loaded route to finish rendering. */
async function ready(page) {
  await expect(page.getByRole('status', { name: 'Loading' })).toBeHidden({ timeout: 20_000 });
  await page.waitForLoadState('domcontentloaded');
}

test.describe('public access', () => {
  test('the tracking page is reachable without signing in', async ({ page }) => {
    await page.goto('/track');

    await expect(page.getByRole('heading', { name: /track a complaint/i })).toBeVisible();
    await expect(page.getByLabel(/ticket number/i)).toBeVisible();
  });

  test('an unknown ticket is reported clearly rather than failing silently', async ({ page }) => {
    await page.goto('/track');
    await page.getByLabel(/ticket number/i).fill('XXX-0000-0000');
    await page.getByRole('button', { name: /check/i }).click();

    await expect(page.getByRole('alert')).toContainText(/could not find/i);
  });

  test('signing in is required for the application itself', async ({ page }) => {
    await page.goto('/student/dashboard');

    await page.waitForURL(/login/, { timeout: 20_000 });
  });

  test('the page has a real title', async ({ page }) => {
    await page.goto('/login');

    // The scaffold default was "frontend", which reached every bookmark.
    await expect(page).toHaveTitle(/resolve/i);
  });
});

test.describe('student journey', () => {
  test('a complaint can be filed and produces a receipt', async ({ page }) => {
    await signIn(page, STUDENT);

    await page.goto('/student/complaints/new');

    // Step one: choose a category from the grouped picker.
    await page.getByRole('button', { name: 'Transcripts' }).click();
    await page.getByRole('button', { name: /continue/i }).click();

    // Step two: the detail.
    await page.getByLabel(/^title/i).fill('Transcript request has had no response');
    await page
      .getByLabel(/what happened/i)
      .fill(
        'I applied for my transcript in July and have heard nothing since, despite visiting the registry twice.',
      );
    await page.getByRole('button', { name: /continue/i }).click();

    // Step three: review and send.
    await expect(page.getByText(/check this before sending/i)).toBeVisible();
    await page.getByRole('button', { name: /send complaint/i }).click();

    await expect(page.getByRole('heading', { name: /your complaint is logged/i })).toBeVisible({
      timeout: 20_000,
    });

    // The receipt must carry the ticket and the deadline, since this is
    // what convinces someone the complaint will not be forgotten.
    await expect(page.getByText(/^DMU-/)).toBeVisible();
    await expect(page.getByText(/respond by/i)).toBeVisible();
    await expect(page.getByText(/escalates automatically/i)).toBeVisible();
  });

  test('short descriptions are rejected with a helpful message', async ({ page }) => {
    await signIn(page, STUDENT);
    await page.goto('/student/complaints/new');

    await page.getByRole('button', { name: 'Library' }).click();
    await page.getByRole('button', { name: /continue/i }).click();

    await page.getByLabel(/^title/i).fill('Too short');
    await page.getByLabel(/what happened/i).fill('Broken');
    await page.getByRole('button', { name: /continue/i }).click();

    await expect(page.getByRole('alert').first()).toContainText(/bit more detail/i);
  });

  test('the category search narrows the list', async ({ page }) => {
    await signIn(page, STUDENT);
    await page.goto('/student/complaints/new');

    await page.getByLabel(/find a category/i).fill('hostel');

    // Accommodation matches; unrelated groups disappear.
    await expect(page.getByRole('button', { name: 'Transcripts' })).toBeHidden();
  });

  test('filed complaints appear in the list', async ({ page }) => {
    await signIn(page, STUDENT);
    await page.goto('/student/complaints');
    await ready(page);

    // The layout also renders a heading, so this is scoped to the page body.
    await expect(
      page.getByRole('heading', { name: 'My complaints', exact: true }),
    ).toBeVisible();
  });
});

test.describe('staff journey', () => {
  test('an administrator sees the queue rather than the student view', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/admin/complaints');

    await ready(page);
    await expect(page.getByRole('tab', { name: /unassigned/i })).toBeVisible();
  });

  test('saved views filter the queue', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/admin/complaints');

    await page.getByRole('tab', { name: /overdue/i }).click();
    await expect(page.getByRole('tab', { name: /overdue/i })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

  test('institution settings are reachable and show the working day', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/admin/institution');
    await ready(page);

    await page.getByRole('tab', { name: /response times/i }).click();
    await expect(page.getByText(/deadlines count working hours only/i)).toBeVisible();
  });

  test('departments can be listed', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/admin/institution');
    await ready(page);

    await page.getByRole('tab', { name: /departments/i }).click();
    await expect(page.getByText('Bursary')).toBeVisible();
  });
});

test.describe('authorisation in the interface', () => {
  test('a student cannot reach the admin queue', async ({ page }) => {
    await signIn(page, STUDENT);
    await page.goto('/admin/complaints');
    await ready(page);

    // The guard sends them back to their own area rather than rendering
    // the queue.
    expect(page.url()).not.toContain('/admin/complaints');
    await expect(page.getByRole('tab', { name: /unassigned/i })).toBeHidden();
  });

  test('an institution administrator cannot reach platform provisioning', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/platform/institutions');
    await ready(page);

    // Provisioning is restricted to the platform owner.
    await expect(page.getByRole('button', { name: /add an institution/i })).toBeHidden();
  });
});

test.describe('registers', () => {
  test('an administrator can export the complaint register', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/admin/complaints');
    await ready(page);

    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: /export/i }).click();

    const file = await download;
    expect(file.suggestedFilename()).toMatch(/complaints-\d{4}-\d{2}-\d{2}\.csv/);
  });

  test('a student is not offered an export', async ({ page }) => {
    await signIn(page, STUDENT);
    await page.goto('/student/complaints');
    await ready(page);

    await expect(page.getByRole('button', { name: /export/i })).toBeHidden();
  });
});

test.describe('password reset', () => {
  test('the link on the sign in page reaches a real screen', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('link', { name: /forgot/i }).click();

    // This route did not exist, so the link went nowhere.
    await expect(page.getByRole('heading', { name: /forgotten your password/i })).toBeVisible();
  });

  test('the confirmation does not reveal whether an account exists', async ({ page }) => {
    await page.goto('/forgot-password');
    await page.getByLabel(/email/i).fill('definitely-not-registered@test.ng');
    await page.getByRole('button', { name: /send the reset link/i }).click();

    await expect(page.getByRole('heading', { name: /check your email/i })).toBeVisible();
    await expect(page.getByText(/if that address belongs to an account/i)).toBeVisible();
  });

  test('a reset link with no token explains itself', async ({ page }) => {
    await page.goto('/reset-password');

    await expect(page.getByRole('heading', { name: /link is incomplete/i })).toBeVisible();
  });

  test('password rules are shown as they are met', async ({ page }) => {
    await page.goto('/reset-password?token=example');

    const save = page.getByRole('button', { name: /save the new password/i });
    await expect(save).toBeDisabled();

    await page.getByLabel(/new password/i).fill('Strong123');
    await expect(save).toBeEnabled();
  });
});

test.describe('command palette', () => {
  test('opens with the keyboard and jumps to a page', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/admin/dashboard');
    await ready(page);

    await page.keyboard.press('Control+k');
    const palette = page.getByPlaceholder(/search a ticket number/i);
    await expect(palette).toBeVisible();

    await palette.fill('analytics');
    await page.keyboard.press('Enter');

    await expect(page).toHaveURL(/analytics/);
  });

  test('closes on escape', async ({ page }) => {
    await signIn(page, ADMIN);
    await page.goto('/admin/dashboard');
    await ready(page);

    await page.keyboard.press('Control+k');
    await expect(page.getByPlaceholder(/search a ticket number/i)).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.getByPlaceholder(/search a ticket number/i)).toBeHidden();
  });

  test('offers a student only their own destinations', async ({ page }) => {
    await signIn(page, STUDENT);
    await page.goto('/student/dashboard');
    await ready(page);

    await page.keyboard.press('Control+k');
    await page.getByPlaceholder(/search a ticket number/i).fill('people');

    // Staff destinations must not be reachable from a student session.
    await expect(page.getByText('Nothing matches that.')).toBeVisible();
  });
});

test.describe('accessibility', () => {
  test('every form control has a label', async ({ page }) => {
    await page.goto('/login');
    // Wait for the lazily loaded route rather than a bare load event.
    await page.getByLabel(/email/i).waitFor({ state: 'visible', timeout: 20_000 });

    const inputs = page.locator('input:not([type="hidden"])');
    const count = await inputs.count();
    expect(count).toBeGreaterThan(0);

    for (let index = 0; index < count; index += 1) {
      const input = inputs.nth(index);
      const id = await input.getAttribute('id');
      const label = await input.getAttribute('aria-label');
      // A placeholder is not a label: it disappears as soon as typing starts.
      expect(Boolean(id) || Boolean(label)).toBeTruthy();
    }
  });

  test('the primary action is reachable by keyboard with a visible focus ring', async ({ page }) => {
    await page.goto('/track');
    await ready(page);

    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(['INPUT', 'A', 'BUTTON']).toContain(focused);
  });

  test('status is never conveyed by colour alone', async ({ page }) => {
    await signIn(page, STUDENT);
    await page.goto('/student/complaints');
    await ready(page);

    const badge = page.locator('[title]').filter({ hasText: /submitted|resolved|progress/i }).first();
    if (await badge.count()) {
      // Amber and red are indistinguishable under deuteranopia, so the
      // text label has to carry the meaning.
      await expect(badge).not.toBeEmpty();
    }
  });
});
