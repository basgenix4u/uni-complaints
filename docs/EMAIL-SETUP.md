# Email: how it actually works, and what to set up

Resolve sends no email of its own. It hands messages to a provider you
choose, over ordinary SMTP. Nothing in the code is tied to one supplier,
so you can change your mind later by editing four environment variables.

This matters more than it sounds, because **email is what confirms a
student's address, and an account that cannot confirm cannot file a
complaint.** Get this wrong and the product does not work.

---

## What happens without a provider

Messages are written to a queue table and stay there. They are not lost
and they are not marked failed: the moment you configure a provider, the
next sweep sends the whole backlog.

This is deliberate. An earlier version treated "no provider" as a
delivery failure, retried five times, and gave up — so by the time
anybody configured SMTP the queue was already dead and every student who
had registered was permanently locked out.

While there is no provider:

- Administrators see a warning on **Registrations** and **Invite staff**.
- `GET /api/admin/delivery-health` reports `not_configured`.
- An administrator can confirm a student's address by hand, so the
  institution is never completely stuck.

---

## The four settings

```bash
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
MAIL_FROM="Resolve <no-reply@yourdomain.ng>"

# Must match the deployed front end. Confirmation links are built from it,
# so if it is wrong every link in every email points at the wrong place.
APP_URL=https://your-frontend-domain
```

Port 587 uses STARTTLS; port 465 is encrypted from the first byte. Both
are handled, and the right one is chosen from the port number. A relay
that offers neither is refused when a password is set, rather than
sending your credentials in the clear.

---

## Which provider

You need a **transactional** email provider. A normal mailbox is the
wrong tool: personal Gmail caps you at a few hundred a day and will
eventually treat the traffic as suspicious.

| Provider | Free tier | Notes |
|---|---|---|
| **Brevo** (formerly Sendinblue) | 300/day, no card | Easiest start. Works from Nigeria without a US entity |
| **Resend** | 3,000/month | Cleanest setup; needs a domain you control |
| **Mailgun** | Trial, then paid | Long-standing, good deliverability |
| **Amazon SES** | 3,000/month for a year | Cheapest at volume, fiddliest to approve |
| **Gmail / Google Workspace** | ~500/day | Requires an App Password, not your login password. Fine for a pilot, not for a whole university |

For a first institution, 300 messages a day is more than enough:
registrations are a trickle after the opening week, and routine
acknowledgements stay inside the application rather than being emailed.

### Brevo, concretely

1. Sign up, then open **SMTP & API → SMTP**.
2. Copy the server, port, login and **SMTP key** (not your account
   password).
3. Set:
   ```bash
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USERNAME=<the login Brevo shows>
   SMTP_PASSWORD=<the SMTP key>
   MAIL_FROM="Resolve <no-reply@yourdomain.ng>"
   ```
4. Verify your sending domain in Brevo, or mail will land in spam.

---

## Make it arrive, not just send

Sending is the easy half. Nigerian universities use Microsoft 365 and
Google Workspace heavily, and both are unforgiving about unauthenticated
mail. Add two DNS records for your domain:

- **SPF** — a TXT record naming your provider as allowed to send for you.
  Your provider gives you the exact value.
- **DKIM** — a TXT record holding a signing key, also from your provider.

Without these a confirmation link is likely to be filed as spam, which
looks exactly like the email never arriving.

`MAIL_FROM` must use a domain you control. Putting `@gmail.com` there
fails DMARC and is rejected outright by many institutions.

---

## Checking it works

```bash
# Is a provider configured, and is anything stuck?
curl -H "Authorization: Bearer <admin token>" \
  https://your-api/api/admin/delivery-health
```

```json
{ "email": { "state": "ok", "queued": 0, "failed": 0 } }
```

`state` is one of:

| State | Meaning |
|---|---|
| `ok` | A provider is configured |
| `console` | Messages are being written to the log instead of sent — testing only |
| `not_configured` | Nothing set up; messages are held, and registrations need confirming by hand |

The queue is drained by `flask send-queue`, which the scheduler already
runs every five minutes. On the free hosting tier the GitHub Actions
workflow calls `POST /api/tasks/all`, which includes it.

---

## Local development

Reading mail out of the log is easier than running a mail server:

```bash
MAIL_TO_CONSOLE=true
```

Every message is logged in full, confirmation link included. **Production
refuses to start with this enabled** — a confirmation link is a
credential, and logs are read by more people than inboxes are.

To test a real SMTP path instead, any local catcher works:

```bash
pip install aiosmtpd
python -m aiosmtpd -n -l localhost:1025
# then: SMTP_HOST=localhost SMTP_PORT=1025
```

---

## SMS

Entirely separate, entirely optional, and off unless configured. Only one
event is ever texted: a complaint passing its deadline. Data runs out, but
a phone still receives SMS, and that is the message worth the cost.

```bash
SMS_PROVIDER=termii          # or africastalking
TERMII_API_KEY=...
SMS_SENDER_ID=Resolve
```

Nothing depends on SMS. Leave it unset and the product works.

---

## If email is simply not available yet

You can run an institution without it, so long as somebody accepts the
work:

1. Set the institution's verification mode to `manual` or `register`.
2. Registrations appear under **Registrations** with the reason they are
   waiting.
3. The administrator uses **Confirm it for them** to settle the address,
   having checked by whatever means they trust.
4. Staff accounts still need the invitation link, so read it from the
   queue:
   ```sql
   SELECT recipient, body FROM outbound_messages
   WHERE status = 'pending' ORDER BY created_at DESC LIMIT 20;
   ```

Workable for a pilot of a few dozen. Not workable for a university, and
it puts a person in the loop for something a provider does for free — so
treat it as a bridge, not a plan.
