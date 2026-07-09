# Farm I-9

A custom [Frappe](https://frappeframework.com/) app that adds an **I-9
employment eligibility verification workflow** to an ERPNext v15 site. Built for
farm/agriculture operations that run seasonal harvest hiring and need a
defensible I-9 process without the heavyweight HR-SaaS price tag.

Farm-labor SaaS (FieldClock and friends) does **not** offer an I-9 workflow —
this app is the differentiator in the FAFO product bundle.

> **Phase 1 scope.** This release delivers the data model, controllers, audit
> logging, and configuration. The public `/hire` web form, combined USCIS PDF
> generation, e-signature capture, and Spanish translation arrive in later
> phases (see the roadmap below).

## The core design decision: audit posture

Federal law lets an employer either **photocopy** I-9 documents (maximum
audit-defense) **or** run **attestation only** (minimum PII exposure). Both are
legal — *as long as the employer is uniform across all employees* (INA §274B
anti-discrimination). This app makes that a single per-site switch:

- **I-9 Settings → Store Document Copies** — the key flag. When on, the I-9 Form
  shows a document-copies table and requires at least one copy before a record
  can be marked Complete. When off, no copies are collected.
- **I-9 Settings → Enrolled in E-Verify** — enrolling in E-Verify legally
  requires retaining copies of any List B photo document, so turning this on
  **forces Store Document Copies on** (enforced in the settings controller).
- The I-9 Form controller raises a **uniformity warning** if a record carries
  copies while the site-wide policy says not to store them.

## Per-Company Settings

Multi-entity operators (e.g. a farm plus a packing house, each its own ERPNext
**Company**) can give each Company its own audit posture. Create an **I-9
Company Settings** record for a Company and set any of the same fields exposed on
global I-9 Settings — `store_document_copies`, `enrolled_in_e_verify`,
`notification_email`, the reminder windows, `preferred_language`, and the
business identity overrides (`business_legal_name`, `business_address`,
`business_ein`).

The I-9 Form controller reads these fields through a single resolver,
`get_effective_setting(company, field_name)`:

1. If an **I-9 Company Settings** record exists for the form's Company and the
   field is set, that value wins.
2. Otherwise the value falls back to the global **I-9 Settings** Single.

Text fields (email, address, name, EIN) count as "set" only when non-empty. For
Check/Int/Select fields, any stored value is treated as an explicit override —
`0` is a legitimate choice, so an existing Company Settings record with
`store_document_copies = 0` deliberately opts that Company *out* even when the
global default is on. Companies with no I-9 Company Settings record behave
exactly as before, using global Settings. E-Verify enrollment forces copy
retention at the Company level too, mirroring the global rule.

### Migration note

**Phase 1.2 requires no data migration.** Existing installs keep working
unchanged — every Company that lacks an I-9 Company Settings record simply uses
global I-9 Settings, identical to Phase 1.1. Creating per-Company records is
entirely optional.

## What's in the box

| DocType | Purpose |
|---|---|
| **I-9 Form** | One hire record per employee. Section 1 (employee) + Section 2 (employer), retention dates, optional document copies. Naming series `I9-.YYYY.-.####`. |
| **I-9 Settings** | Single DocType. The audit-posture config flags + business identity + reminder windows. Global fallback for every Company. |
| **I-9 Company Settings** | Optional per-Company override of the I-9 Settings fields. One record per Company (named by Company). Any field left blank/unset falls back to global I-9 Settings. |
| **I-9 Audit Log** | Append-only, immutable audit trail. No write/delete/amend role for anyone. |
| **I-9 Document Type** | Lookup of current USCIS List A/B/C acceptable documents, pre-seeded via fixtures. |
| **I-9 Form Document** | Child table: one attached document copy (only used when Store Document Copies is on). |

### Encoded legal rules

- **Section 1** (employee attestation) can be electronic, on/before day 1.
- **Section 2** (employer verification) requires in-person original-document
  review within 3 business days of hire.
- **Retention** = `MAX(hire_date + 3 years, termination_date + 1 year)` —
  auto-calculated on every save.
- **Uniformity** (§274B) enforced at the Settings flag.
- **E-Verify** enrollment forces copy retention.

## Install

This app installs alongside ERPNext on the Umbrel deployment. In the
`fafo-erpnext` image build:

```dockerfile
RUN cd /home/frappe/frappe-bench && \
    bench get-app farm_i9 https://github.com/polehntim-commits/farm_i9.git
```

Then, in `entrypoint.sh` (after the erpnext + agriculture install):

```bash
su frappe -s /bin/bash -c "bench --site $SITE_NAME install-app farm_i9"
```

For a local dev bench:

```bash
cd ~/frappe-bench
bench get-app farm_i9 /path/to/farm_i9      # or the GitHub URL
bench --site your.site install-app farm_i9
bench --site your.site migrate
```

The `I-9 Document Type` lookup is seeded automatically from
`farm_i9/fixtures/i_9_document_type.json` on install/migrate.

## Testing notes (Phase 1, no live bench in the build sandbox)

1. **Settings** → open *I-9 Settings*, toggle **Enrolled in E-Verify** → confirm
   **Store Document Copies** auto-enables with a message.
2. **New I-9 Form** → fill Section 1 fields → save → status auto-advances to
   *Section 1 Complete* and `section_1_signed_date` is stamped.
3. Enter an SSN as `123-45-6789` → saved as `123456789`, masked field shows
   `***-**-6789`.
4. Set `citizenship_status = Authorized Alien` → alien number + work-auth
   expiration become required and visible.
5. Choose **Document Path = List A** → only List A fields show; switch to
   **List B + List C** → both List B and List C blocks show.
6. Fill Section 2 documents + first day of employment → status advances to
   *Complete*, `employer_signed_date` + `hire_date` + `retention_until` set.
7. With **Store Document Copies** on, completing a form with no copies should be
   blocked.
8. Open **I-9 Audit Log** → confirm create/update entries appear and that the
   list is read-only (no edit/delete).

## Roadmap

- **Phase 2** — public `/hire` web form (captures real Section 1 signature IP),
  e-signature canvas, email reminders for doc expiration & destruction.
- **Phase 3** — auto-generated combined I-9 PDF from the USCIS template; Spanish
  translation (`preferred_language`).
- **Phase 4** — USCIS form-version auto-check.

## Repo

Destined for `polehntim-commits/farm_i9`. Developed in-place under
`fafo-umbrel-store/` and split into its own repo before the fafo-erpnext
Dockerfile is wired to `bench get-app` it.

## License

MIT — see [LICENSE](LICENSE).
