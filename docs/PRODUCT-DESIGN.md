# From demo to product: what the real thing needs

**Status:** design discussion, not yet built. Nothing here is implemented.

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
| Students from different universities | ✗ registration silently accepts any institution slug, and the form does not even ask |
| Different complaints go to different units | ✗ **no routing exists.** Category and department are unrelated fields |
| Faculties differ per university | ✗ **hardcoded list of 10 in the frontend.** Same for every institution |
| Students belong to departments | ✗ `faculty` and `department_name` are free text on the user, linked to nothing |
| Non-onboarded schools should be blocked | ◑ partially — it checks the institution exists, but there is no request-to-join path |
| Should not require a university email | ✓ correct today, any email works |
| Google sign-in | ✗ not implemented |
| Email verification | ✗ **none.** Anyone can register claiming any email |

Two of these are serious. **No routing** means every complaint lands in
one undifferentiated pile. **No email verification** means nothing stops
someone registering as a student who is not one.

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

| Stage | Work | Why this order |
|---|---|---|
| **1** | Faculties, departments, units as real tables. Student linked to them | Nothing else can be built on free text |
| **2** | Invitations and bulk import for staff | Removes the hand-typing problem |
| **3** | Routing rules, and escalation up the real hierarchy | The core product gap |
| **4** | Institution directory, request-to-join, interest signal | Makes registration honest and captures demand |
| **5** | Email verification, then Google sign-in | Verification first; Google is an accelerator on top |
| **6** | Student register import and matric verification | Depends on 1 and 5 |
| **7** | Onboarding wizard for institution admins | Packages 1 to 6 into something self-service |
| **8** | Confidential queues, Dean role, appeals | Refinement once the shape is proven |

**Stage 1 is unavoidable and everything depends on it.** It is also a
migration: `faculty` and `department_name` become foreign keys.

---

## 8. Things worth deciding before building

These are genuine forks, and I do not think I should pick for you.

1. **Is the customer the university, or the student?** If universities
   pay, the product is an administrative tool and the SUG is a
   stakeholder. If students are the audience, it is closer to advocacy,
   and a university that ignores complaints is the story rather than the
   customer. This changes what gets built.

2. **What happens to a complaint the institution ignores?** The escalation
   currently stops at the top of the institution. Does it stop there, or
   does something else happen?

3. **Anonymous complaints.** Already supported, off by default. Harassment
   cases are exactly where they matter and exactly where they are hardest
   to act on.

4. **One account across institutions?** A student who transfers, or a
   graduate who still has an open complaint.

5. **Polytechnics and colleges** use different words for the same things:
   Rector rather than Vice-Chancellor, School rather than Faculty. Worth
   deciding now whether the language adapts per institution type.

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
