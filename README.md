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
| **W-4 Form** | Federal income-tax withholding election (2020+ five-step redesign), one record per employee per filing. Company + Employee links, SSN masking, Step 3 dependent-credit auto-calc, signed-PDF legal record. Naming series `W4-.YYYY.-.####`. |
| **I-9 Settings** | Single DocType. The audit-posture config flags + business identity + reminder windows. Global fallback for every Company. |
| **I-9 Company Settings** | Optional per-Company override of the I-9 Settings fields. One record per Company (named by Company). Any field left blank/unset falls back to global I-9 Settings. |
| **I-9 Audit Log** | Append-only, immutable audit trail. No write/delete/amend role for anyone. |
| **I-9 Document Type** | Lookup of current USCIS List A/B/C acceptable documents, pre-seeded via fixtures. |
| **I-9 Form Document** | Child table: one attached document copy (only used when Store Document Copies is on). |

### Employee auto-fill (Phase 1.2.1)

Picking an **Employee** on a new I-9 Form auto-fills Section 1 and part of
Section 2 from the record ERPNext already stores — no retyping data HR collected
at onboarding:

- **Section 1:** legal last/first name, middle initial (trimmed to one
  uppercase character), date of birth, email, phone, and the mailing address
  (street, apt, city, state, zip).
- **Section 2:** first day of employment (from the Employee's date of joining).

Simple 1:1 copies use Frappe `fetch_from` on the field; the middle initial and
address are resolved in the controller (`populate_employee_defaults`) because a
full middle name won't fit a 1-char field and the address is a linked DocType,
not plain text.

**What stays manual — on purpose.** SSN, citizenship/attestation
(`citizenship_status`, alien registration, work-authorization expiration), and
all Section 2 document-verification fields are never auto-filled. They are I-9
attestations the employee/employer must supply directly.

**Auto-fill never overwrites.** Every fetched field uses `fetch_if_empty: 1` (and
the controller only writes fields still blank), so anything you have already
typed is preserved — even if you re-pick the same Employee. You can always type
over a suggested value.

**Address source.** The address is resolved from the Employee's
`current_address` link. Some ERPNext installs keep the mailing address on
`permanent_address` instead — Phase 1.2.1 uses `current_address`; switching to
the other field is a one-line config change in `populate_employee_defaults`.

## W-4 Form (Phase 2.1)

The **W-4 Form** captures an employee's federal income-tax withholding election
on the IRS's 2020+ redesigned form. It follows the same architecture as the I-9
Form — Company-anchored, Employee-linked, auto-filled where possible, with a
signed PDF as the legal record.

**Fields, grouped by the form's five steps:**

- **Company & Legal Entity** — `company` (auto-fills from Employee) and
  `tax_year` (defaults to the current year in `before_insert`; a new W-4 is
  filed at hire and re-filed on life-event changes).
- **Employee** — `employee` link plus name and mailing address, auto-filled the
  same way as the I-9 (`fetch_from` for the 1:1 copies; the controller resolves
  the one-character middle initial and the linked Address). `ssn` is `permlevel: 1`
  restricted PII, stored as a bare 9-digit string with a masked `ssn_masked`
  display copy (`***-**-XXXX`).
- **Step 1 — Filing Status** — Single / Married filing jointly / Head of household.
- **Step 2 — Multiple Jobs or Spouse Works** — single checkbox (collapsible).
- **Step 3 — Claim Dependents** — qualifying children under 17 and other
  dependents; `total_credit_amount` auto-calculates as
  `(children × $2,000) + (other dependents × $500)`, both server-side on save
  and client-side in real time as you type.
- **Step 4 — Other Adjustments** — 4(a) other income, 4(b) deductions, 4(c)
  extra withholding (collapsible, optional).
- **Exemption** — `claim_exempt` checkbox. Exempt status is valid for one year
  only and must be refiled by Feb 15 of the following year.
- **Signature** — `status` (Draft → Signed → Superseded), `signed_date`,
  `signature_ip` (Phase 2 placeholder), and `w4_pdf_attachment`.
- **Retention** — `superseded_by` (links a newer W-4 that replaced this one; the
  old record stays for audit) and `retention_until`.

**Encoded rules.**

- **Signing requires the legal record.** A W-4 cannot move to `Signed` without an
  attached PDF *and* a Company anchor — the controller blocks the transition
  otherwise.
- **Retention** = `signed_date + 5 years` — a simplification of the IRS rule
  (4 years after the tax-return due date or after the tax is paid, whichever is
  later), stamped automatically when the form is signed.
- **Audit log integration.** Create/update/delete events write to the same
  append-only **I-9 Audit Log** used for I-9 activity — one shared compliance
  ledger. W-4 rows leave the `Reference I-9` link null and carry the W-4 name in
  the JSON details payload; the raw SSN is redacted from update diffs.

Withholding is **not** computed here — that's the Phase 3 payroll engine. This
form only records the election.

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
