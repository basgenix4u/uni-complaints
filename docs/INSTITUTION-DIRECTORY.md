# The institution directory

Researched September 2026.

## How many institutions there actually are

The figure of "2,000 plus universities" that gets repeated is not right,
and the real number matters because it decides whether a dropdown is
usable or has to be a search.

Nigeria has **three separate regulators**, and the confusion comes from
adding their registers together:

| Regulator | Sector | Count |
|---|---|---|
| NUC | Universities | **309** |
| NBTE | Polytechnics, monotechnics, technical and allied colleges | **807** |
| NCCE | Colleges of education and NCE-awarding institutions | **255** |

**Around 1,370 tertiary institutions in total.** Not 2,000, but far too
many for a dropdown, and easily enough that search quality decides
whether sign-up works.

### Universities — 309

The NUC approved 33 new universities during 2025, taking the total to
309: **168 private, 74 federal, 67 state**. Private institutions are now
the majority and the fastest-growing group, up from zero in 1990.

Different sources disagree because they count at different dates and
some exclude specialised or open-distance institutions. 309 is the NUC's
own figure and the one to quote.

### Polytechnics and allied institutions — 807

NBTE's own summary is the widest register of the three:

| Category | Public | Private | Total |
|---|---|---|---|
| Polytechnics | 91 | 103 | 194 |
| Specialised institutions | 50 | 93 | 143 |
| Colleges of agriculture | 31 | 1 | 32 |
| Colleges of health science | 66 | 65 | 131 |
| Colleges of nursing science | 92 | 62 | 154 |
| Technical colleges | 150 | 3 | 153 |
| **Total** | **480** | **327** | **807** |

NBTE also **revoked 136 licences** in its 2025 reform round, which is a
reminder that this list shrinks as well as grows.

### Colleges of education — 255

NCCE accredits 255 NCE-awarding institutions: 29 federal, 54 state, 166
private.

## What we ship

`backend/data/institutions.json` holds **455 institutions** — 191
universities, 180 polytechnics, 84 colleges of education — every one
with a state, a slug and, where it is known, the acronym people actually
use.

This is a subset, not the full 1,370. It covers the degree- and
diploma-awarding institutions students are most likely to be complaining
about, and deliberately excludes technical colleges, colleges of nursing
and most health colleges for now. Those are real institutions with real
complaints; they are simply not where a pilot starts.

The list is a **snapshot**. Thirty-three universities were approved in a
single year and 136 technical licences were revoked in the same period,
so it will go out of date. `flask seed-directory` is written to be run
again whenever the file is refreshed: it adds what is new, updates what
has changed, and never touches an institution that has since onboarded,
because its own administrators may have corrected details we imported.

Sources are Wikipedia's regulator-derived lists, cross-checked against
the NUC and NBTE figures above. Wikipedia is used because neither the
NUC nor NBTE publishes a machine-readable register; where its totals
fall short of the official count, the gap is in recently approved
private institutions.

## Why a search and not a dropdown

Four hundred and fifty options is not a dropdown. It is also not a plain
substring filter, because the names collide badly:

- Searching `lagos` matches a dozen institutions.
- Searching `ibadan` matched Ibadan City Polytechnic before the
  University of Ibadan, because the polytechnic's name *starts* with the
  town. Ranking a prefix above a whole-word match was the bug.
- Nobody types "University of Lagos". They type **UNILAG**.

So results are ranked rather than filtered:

1. Exact acronym — `UNILAG` means one institution and nothing else
2. Exact name
3. Acronym prefix
4. Whole word anywhere in the name — this is what fixes `ibadan`
5. Name prefix
6. Anything else

Within a tier: institutions already using Resolve first, then
universities before polytechnics before colleges, then federal before
state before private, then shorter names. The sector ordering is a
heuristic about what people search for — someone typing a town name
usually wants the big university there — not a judgement about quality.

Ranking happens in Python over a capped candidate set rather than in
SQL, so the ordering is identical on SQLite and PostgreSQL.

## Acronyms

`short_name` is separate from `code` on purpose. `code` prefixes every
ticket number, so it has to be unique; acronyms are not. Several
institutions reduce to ACE.

Roughly eighty acronyms are set by hand because deriving them from
initials produces nonsense — the University of Lagos comes out as "UL".
The rest are generated initials, which are a reasonable search hint even
when nobody says them aloud.

## Institutions that have not signed up

Every imported institution starts as **not onboarded**. A student who
finds theirs is told it is known but not yet using Resolve, and can ask
to be notified — which is a far better answer than "we have never heard
of it", and the accumulated requests are the argument for approaching
that institution.

## Refreshing the list

```bash
DB_SCHEMA=resolve flask seed-directory
```

Safe to run repeatedly. Reports what it added, updated and left alone.
