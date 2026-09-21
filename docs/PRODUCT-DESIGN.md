# From demo to product: what the real thing needs

**Status:** stages 1 to 5 of section 7 are built and merged, and stage 6
in part. The rest is still design. Section 7 records which is which.

You are right that the current build is a working demo rather than a
product. It assumes one institution with a flat list of departments, and
almost everything about how a Nigerian university actually works is
missing. This is an attempt to think it through properly before writing
code.

---

## 1. What is actually broken today

I checked the code rather than guessing.

| Your observation | What the code does now |
|---|---|
| Staff must be insiders | ✓ correct — staff are created by an admin, never self-registered |
| Students from different universities | ✓ **fixed in stage 4.** A searchable directory, and the form asks |
| Different complaints go to different units | ✓ **fixed in stage 3.** Routing rules, owned by the institution, applied at filing |
| Faculties differ per university | ✓ **fixed in stage 1.** Faculties and departments are per-institution tables |
| Students belong to departments | ✓ **fixed in stage 1.** The student register carries faculty, department and level |
| Non-onboarded schools should be blocked | ✓ **fixed in stage 4.** Refused, and the interest is recorded instead |
| Should not require a university email | ✓ correct today, any email works |
| Google sign-in | ✗ not implemented |
| Email verification | ✓ **fixed in stage 5.** Confirmed before an account may file |

Both of the serious ones are now fixed. **No routing** meant every
complaint landed in one undifferentiated pile. **No email verification**
meant nothing stopped someone registering as a student who was not one.
Google sign-in remains the notable gap, and it is an accelerator on top
of verification rather than a replacement for it.

---

## 2. How a Nigerian university is actually shaped

Two hierarchies exist side by side, and a complaint can enter either.

### Academic — where a student sits
```
Institution
└── Faculty              Engineering, Science, Law, Arts
    └── Department       Computer Engineering, Civil, Mechanical
        └── Programme    B.Eng Computer Engineering
            └── Level    100, 200, 300, 400, 500
```

A student belongs to exactly one path through this. It is also where
academic complaints are resolved: a grade dispute goes to the Head of
Department, then the Dean, and only then beyond the faculty.

### Administrative — who resolves things
```
Institution
├── Registry           admissions, records, transcripts, certificates
│   ├── Exams & Records
│   └── Admissions
├── Bursary            fees, receipts, refunds, scholarships
├── Student Affairs    hostel, welfare, discipline, SUG oversight
├── ICT / MIS          portal, email, course registration faults
├── Security           safety, theft, harassment reports
├── Health Services    clinic
├── Library
├── Works & Maintenance  water, electricity, buildings
└── SUG                student-led, advocacy rather than authority
```

**The distinction that matters:** a complaint about a missing result is
academic and belongs to a department. A complaint about a fee receipt is
administrative and belongs to Bursary. The current model cannot express
the difference, because `Department` is one flat list used for both.

### What differs between universities

Anyone building this for more than one institution has to accept:

- **Faculty names differ.** "Management Sciences" at one, "Administration"
  at another.
- **Unit names differ.** Some have a Registry with divisions under it,
  others have Academic Affairs as a peer.
- **Routing differs.** At one university scholarships sit with Student
  Affairs; at another with Bursary.
- **Matric formats differ.** `ENG/COE/21/013`, `U19CS1001`, `2019/1/12345CS`.
  The current single regex is wrong for most institutions.
- **SUG involvement differs.** Some route welfare complaints through the
  SUG first; others treat it as advisory only.

**Conclusion: none of this can be hardcoded.** It has to be data the
institution configures during onboarding.

---

## 3. The four problems, and how I would solve them

### Problem A — a student registers for a school that is not onboarded

Today the registration fails with "we could not find that institution",
which is a dead end and tells us nothing.

**Proposal: turn the dead end into demand signal.**

```
Student picks their institution from a searchable list
│
├── Onboarded and active
│      → normal registration
│
├── Known to us, not yet onboarded
│      → "Federal University Wukari is not using Resolve yet.
│         Leave your email and we will tell you when it is."
│      → recorded as an interest signal
│
└── Not in the list at all
       → "Tell us your institution" free text
       → creates a lead
```

Seed the list from the NUC register: roughly 260 universities, plus
polytechnics and colleges. A student then always recognises their school,
even before it is a customer.

This matters commercially. Fifty students from one university asking for
it is the strongest possible argument to that university's registrar.

### Problem B — verifying a student really is a student

You are right that requiring a university email is wrong. Many Nigerian
students never receive one, or cannot access it. But accepting any email
with no check means anyone can claim to be a student anywhere.

**Proposal: let each institution choose, because they differ.**

| Method | How it works | Suits |
|---|---|---|
| Open | Any email, verified by a link | Institutions that trust volume over rigour |
| Matric check | Matric must match a list the institution uploads | Most, and the strongest option |
| Domain hint | A university email skips review, others are reviewed | Institutions that issue email reliably |
| Manual | Student Affairs approves each registration | Small institutions, or a pilot |

Default to **matric check**. The institution uploads its student register
during onboarding — a spreadsheet of matric numbers, names and
programmes, which every registry already has. Registration then verifies
against it, and the student's faculty, department and level are filled in
automatically rather than typed.

That single decision removes the fake-student problem and the
"which faculty do I pick" problem at once.

**Email verification becomes mandatory regardless of method.** It does not
prove someone is a student, but it proves they control the address, which
is the minimum for a system that sends resolution notices.

### Problem C — routing a complaint to the right unit

This is the heart of the product and the thing most obviously missing.

**Proposal: routing rules, owned by the institution.**

```
Category              →  Handling unit         →  Fallback
Missing result           Exams & Records          Faculty Dean
Fee receipt not showing  Bursary                  —
Hostel allocation        Student Affairs          —
Portal will not load     ICT                      —
Lecturer conduct         Head of Department       Dean → Registrar
Harassment               Student Affairs          confidential queue
Water supply             Works & Maintenance      —
```

Three refinements that come from how universities really work:

**1. Academic complaints route to the student's own department**, not to a
fixed unit. A Computer Engineering result query goes to Computer
Engineering, and the system already knows the student's department, so
the rule is "route to the complainant's department" rather than a named
one.

**2. Escalation follows the real hierarchy.** Officer → Head of Unit →
Dean or Registrar → Dean of Student Affairs. The current escalation
notifies every department head at once, which is wrong; it should climb
one rung at a time.

**3. Some categories need a confidential queue.** A harassment complaint
naming a lecturer must not be visible to that lecturer's own department.
It should route to a small, named group and stay out of the general
queue.

### Problem D — getting staff in

Staff are insiders, so self-registration is correctly impossible. But
somebody has to create the first one, and asking an admin to type in
three hundred officers is not a product.

**Proposal: invitation, with bulk import.**

```
Platform admin onboards the institution
│  creates the institution and its first Institution Admin
│
Institution Admin
│  imports units, faculties and departments from a spreadsheet
│  invites Unit Heads by email
│
Unit Head
│  invites officers into their own unit only
│
Officer
│  accepts, sets a password, starts work
```

An invitation is a signed, single-use, expiring link. Nobody sets someone
else's password, and nobody outside can join.

---

## 4. What onboarding an institution actually requires

This is the question you asked directly. Working through it:

### Stage 1 — the agreement, before any software
Not code, but it gates everything: who signs, who is the data controller
under the NDPA, and who is the named Data Protection Officer.

### Stage 2 — create the institution
| Field | Why |
|---|---|
| Legal name, short name | Display and ticket prefix |
| Type | University, polytechnic, college, so language adapts |
| NUC or NBTE number | Proves it is real |
| Domains | `@fuwukari.edu.ng`, used as a signal not a requirement |
| Logo, brand colour | The portal should look like theirs |
| Subdomain | `fuw.resolve.ng` |
| Working hours, holidays | SLA clocks already depend on this |

### Stage 3 — the structure
Uploaded as spreadsheets, because that is what registries have:

- **Faculties and departments** — the academic tree
- **Administrative units** — Bursary, Registry, ICT and the rest
- **Matric format** — as a pattern, per institution
- **Student register** — matric, name, programme, level

Ship a starter template with the twelve units almost every Nigerian
university has, so the common case is a review rather than data entry.

### Stage 4 — routing and people
Map each category to a unit, starting from a sensible default. Invite the
unit heads. They invite their own officers.

### Stage 5 — pilot, then open
One faculty for two weeks, then the whole institution. Nothing here is
software; it is how you avoid launching a system nobody was told about.

---

## 5. Sign-in

**Google sign-in: yes, and it is a bigger win than it looks.** Most
Nigerian students have a Gmail account and no reliable university email.
It removes a password to forget, and Google has already verified the
address, so email verification comes free.

Keep passwords as well. Some staff will be on institutional machines
where Google is awkward.

**What must not happen:** Google sign-in creating an account out of
nothing. It authenticates a person; it does not prove they belong to an
institution. The flow is: sign in with Google, then match against the
student register, then the account exists.

---

## 6. Roles

The current five are close but miss the academic side entirely.

| Role | Scope | Can do |
|---|---|---|
| Student | Themselves | File, track, reply, appeal |
| Officer | One unit | Work the queue for their unit |
| Unit Head | One unit | Assign within it, invite officers, see unit performance |
| Dean | One faculty | See academic complaints across their departments |
| Institution Admin | Whole institution | Structure, routing, staff, settings |
| Platform Admin | All institutions | Onboard, suspend, support |

**Dean is the addition.** Academic escalation has nowhere to go without
it — currently a departmental complaint escalates to institution admins,
which is both wrong and unhelpful.

One person may hold a role in more than one unit: a Head of Department is
often also on a faculty committee. That means roles belong on a
membership record, not as a single column on the user.

---

## 7. What I would build, in order

Each stage leaves the system working.

| Stage | Work | Why this order | Status |
|---|---|---|---|
| **1** | Faculties, departments, units as real tables. Student linked to them | Nothing else can be built on free text | **Built** |
| **2** | Invitations and bulk import for staff | Removes the hand-typing problem | **Built**, with the interface added later |
| **3** | Routing rules, and escalation up the real hierarchy | The core product gap | **Built** |
| **4** | Institution directory, request-to-join, interest signal | Makes registration honest and captures demand | **Built** |
| **5** | Email verification, then Google sign-in | Verification first; Google is an accelerator on top | **Verification built.** Google sign-in still to do |
| **6** | Student register import and matric verification | Depends on 1 and 5 | **Built.** Structure and register are managed from the interface |
| **7** | Onboarding wizard for institution admins | Packages 1 to 6 into something self-service | To do |
| **8** | Confidential queues, Dean role, appeals | Refinement once the shape is proven | Queues and the Dean built in 2 and 3; appeals to do |

### Making email real

The gate built in stage 5 had no key. Three things were wrong, and all
three are now fixed:

- An unconfigured provider counted as a delivery failure, so the
  confirmation message retried five times and died. By the time anyone
  set up SMTP the backlog was unrecoverable and every registered student
  was locked out permanently. A missing provider is now a separate state
  that holds the message without spending its retries.
- `starttls()` was called unconditionally, which fails on port 465
  (implicit TLS, used by Gmail and many Nigerian hosts) and on any relay
  not offering it. The right mode is now chosen from the port, and a
  password is never sent over an unencrypted connection.
- Nobody could tell whether email worked. Administrators now see the
  state on screen, and can confirm an address by hand when it does not.

### Stage 2's missing interface

Seven invitation endpoints had shipped with no screen at all, so the only
way to create an officer was a curl request. Routing complaints to units
with nobody in them is not much use, which made this a prerequisite for
stage 3 working in practice rather than only in tests.

### Closing the gap that made stage 6 a claim rather than a feature

An audit against the running application found the academic tables and
the import logic had no HTTP route at all. `verification_mode="register"`
— the documented default and the strongest way to verify a student —
therefore degraded in silence: every registration at every institution
fell through to manual approval, because the register could never be
populated. The trace showed `POST /api/admin/sessions`,
`/faculties` and `/register/import` all returning 404.

Now reachable, and covered end to end:

- Sessions, faculties and academic departments, individually or from a
  pasted tree.
- Register import with a dry run that is not skippable, because the file
  decides who may sign up.
- A searchable register that tolerates how a matriculation number is
  actually typed.
- Correcting one row, and releasing a wrongly claimed one — without
  which the real student is locked out permanently.

Two concurrency defects were found by the same audit and fixed. The
ticket counter was a read-modify-write in Python, so two students filing
at the same moment both read the same value; the unique constraint then
turned the collision into a server error. Status transitions were checked
in Python and written later, so two officers could both pass the check
and the second silently overwrote the first — a complaint resolved by one
and declined by the other ended as whichever committed last. Both are now
single atomic statements, and the losing writer is told rather than
ignored.

### What stages 4 to 6 actually changed

- A public, searchable institution directory. Universities that have not
  signed up are listed and flagged, because "we know them, not yet" leads
  somewhere and "not found" does not.
- Registering against an institution that has not been onboarded is
  refused; the student is offered the interest list instead, and the
  count of who is asking decides who to approach next.
- The registration form searched a directory rather than asking for a
  slug nobody outside the project knows. It also previously sent no
  institution at all, so it could not have worked against the real API.
- The ten hardcoded faculties shown to every university are gone.
  Faculty and department come from the institution's own register.
- Self-registration must confirm its email before filing. Staff who
  accept an invitation are exempt: the link only ever went there.
- Verification gates filing rather than signing in, so somebody who has
  not confirmed can still get in and finish the step.
- `verification_mode` is now enforced rather than merely stored. A
  register match is approved outright and inherits faculty and
  department; no match waits for an administrator rather than being
  refused, because registers are never complete.
- A matriculation number is only demanded where it will be checked.

### What stage 3 actually changed

- `POST /api/complaints` calls `resolve_destination()`, so a complaint
  reaches a named unit without the student choosing one. An explicit
  choice is still honoured.
- A routing rule may override the deadline for its category. A missing
  result and a broken tap are both Registry's and are not the same wait.
- `is_confidential` is copied onto the complaint at filing. Confidential
  work is filtered out of every list, count, chart and export for anyone
  outside the handling unit, and cannot be assigned to them.
- Escalation climbs one rung at a time — handling unit, then the dean or
  the escalation unit, then the institution — instead of notifying every
  department head at once. It never widens a confidential audience.
- What survives the whole climb lands on an ignored report: visible to
  the institution's head, emailed weekly, and visible to the platform as
  ticket numbers only.
- A new institution is provisioned with the standard units and a draft
  routing table, so it works from the first day.

**Stage 1 is unavoidable and everything depends on it.** It is also a
migration: `faculty` and `department_name` become foreign keys.

---

## 8. Things worth deciding before building

These were genuine forks. Most are now settled; the answers are
recorded here so the reasoning is not lost.

1. **Is the customer the university, or the student?** *Decided: neither
   pays. It is free for now.* That keeps the student as the audience
   without making the institution an adversary, and it removes the
   pressure to build billing before the product works.

2. **What happens to a complaint the institution ignores?** *Decided and
   built.* Escalation climbs to the top of the institution and stops
   there. Anything still unanswered after that piles onto an ignored
   list: the institution's head sees it and is emailed it weekly, and
   the platform sees which institutions are not answering — ticket
   numbers only, never the complaints themselves.

3. **Anonymous complaints.** *Decided.* Kept, and they stay. Confidential
   routing now covers the related case: a report naming a member of staff
   is kept out of that person's own unit even when it is not anonymous.

4. **One account across institutions?** A student who transfers, or a
   graduate who still has an open complaint.

5. **Polytechnics and colleges** use different words for the same things:
   Rector rather than Vice-Chancellor, School rather than Faculty.
   *Decided: set aside for now.* The structure already fits both; only
   the labels differ, and that is a later change rather than a blocker.

---

## 9. My honest recommendation

The build quality is good and the foundations are sound: multi-tenancy,
audit trail, SLA, data protection. **What is missing is the domain model
of a university**, and everything you listed traces back to that one gap.

I would do stage 1 first and nothing else, because every other item
depends on it and it is the only one that is a migration rather than an
addition. Get the structure right and the rest is ordinary feature work.

I would also resist building all eight stages before anyone uses it. The
routing table is a guess until a real registrar looks at it and says
"no, scholarships are Bursary here". One institution's structure loaded
for real will teach more than another month of design.
