# Phase 1 Audit Report (Book Publication CRM)

Date: 2026-05-19
Scope: `sales`, `catalog`, `reports`, `accounts`, templates, audit commands

## Executive Summary
- Core workflows exist and are functional: product, inventory, invoicing, payments/refunds, PDF statements.
- Major risks are maintainability and data-consistency edge cases caused by oversized view modules, mixed legacy/refund logic, and broad exception swallowing in critical paths.
- Security/config hardening is intentionally deferred in code because settings changes were explicitly requested to remain unchanged.

## Findings by Severity

### Critical
1. Mixed refund architecture can lead to accounting ambiguity.
- Evidence: both `Payment(is_refund=True)` and legacy `Refund` model are active.
- Files:
  - `sales/models.py`
  - `sales/views.py` (refund and statement flows include both paths)
- Risk: inconsistent net received and statement totals if both paths are used inconsistently.

2. Broad exception swallowing in financial/inventory updates hides failures.
- Evidence: multiple `except Exception` around recalc/allocation flows.
- Files:
  - `sales/views.py`
  - `catalog/views.py`
  - `catalog/inventory_utils.py`
- Risk: silent partial failure with user-success response.

### High
1. `sales/views.py` remains very large and multi-responsibility.
- Evidence: invoice CRUD, payments, refunds, PDF generation, statements, APIs, bulk actions all in one module.
- File:
  - `sales/views.py`
- Risk: high regression probability on edits; difficult review/testing.

2. Duplicate/legacy import and section artifacts still present in places.
- Evidence: cleaned partially, but module still has historical blocks and repeated patterns.
- Files:
  - `sales/views.py`
  - `catalog/views.py`
- Risk: maintainability drag, hidden side effects.

3. Inventory transactional references are flexible but not strictly enforced by schema.
- Evidence: `ref_type/ref_id` text-based conventions across utilities/views.
- Files:
  - `catalog/models_stock.py`
  - `catalog/inventory_utils.py`
  - `catalog/views.py`
- Risk: hard-to-audit edge cases if new code paths use inconsistent `ref_type` values.

### Medium
1. `catalog/tests.py` improved, but coverage still limited relative to feature surface.
- Evidence: basic HSN/model tests present; warehouse/print-run/import-export/invoice-stock edge tests limited.
- Files:
  - `catalog/tests.py`
  - `sales/tests.py`

2. Reports layer has duplicate decorator imports and can be cleaned.
- File:
  - `reports/views.py`

3. Multiple management audit commands exist but no single release-gate script documented.
- Files:
  - `sales/management/commands/audit_sales.py`
  - `catalog/management/commands/audit_inventory.py`

### Low
1. Comment/language consistency and minor text artifacts in templates/code comments.
- Files: various templates and views.

## Workflow Audit Snapshot

### Product + Inventory
- Product CRUD + HSN support present.
- Stock source-of-truth uses StockLedger; print-runs feed stock correctly in intended paths.
- Import/export exists for products and warehouses.

### Invoice + Payments + Refunds
- Invoice create/edit/delete/bin/restore logic exists and linked to stock allocation.
- Bulk actions exist.
- Refund lifecycle exists with PDF and statement support.
- Needs stricter canonical refund path policy.

### Reporting + PDF
- Dashboard and statement views available.
- PDF generation consolidated to helper functions in `sales/utils.py` and used by views.

## Recommended Execution Order (Phase 2+)
1. Canonicalize refund accounting path and update all statement computations to one source policy.
2. Replace critical silent `except Exception` blocks with controlled logging + safe user message + rollback where required.
3. Introduce invariant checks in service helpers (`allocate/commit/reverse`) and enforce allowed `ref_type` set centrally.
4. Expand tests for inventory + refund edge cases and import/export roundtrip.
5. Split `sales/views.py` into domain modules without URL contract changes.

## Acceptance Criteria for Phase 1 Completion
- Findings documented with file-level evidence: done.
- Severity-prioritized remediation order: done.
- Next phase implementation plan unblocked: done.


## Phase Progress Update (2026-05-19)

Completed in codebase:
- HSN end-to-end at product model/form/templates + invoice detail/PDF rendering (safe fallback when missing).
- Product publication metadata fields added: author, imprint, edition, academic_session.
- Product import/export updated for HSN and publication fields.
- PDF option/path logic centralized in `sales/utils.py` and reused.
- Financial aggregate helpers added and reused in statement PDF paths.
- High-risk exception areas now log with context in `sales/views.py` and `catalog/views.py`.
- Basic reports import cleanup done in `reports/views.py`.

Pending for next phases:
- Canonicalize one refund architecture fully (legacy `Refund` vs `Payment.is_refund`).
- Break up `sales/views.py` into smaller domain modules.
- Add broader automated tests for inventory/refund/import-export edge cases.
- Final production cleanup pass for dead templates/helpers only after route-level usage scan.

Validation notes:
- `python manage.py check`: passing.
- Django tests currently blocked locally due to MySQL not running (`WinError 10061` on localhost connection).


## Completion Report (Scope Lock) - 2026-05-19

Completed:
- Product flow stabilization and form cleanup completed.
- HSN (`hsn_code`) integrated across product master, invoice detail/PDF, and safe blank fallback.
- Publication fields added (`author`, `imprint`, `edition`, `academic_session`) with UI + import/export support.
- Missing catalog transaction templates added to prevent route failures.
- Cleanup done for obvious junk/unused files and duplicate imports.
- Refund policy centralized in `sales/utils.py::aggregate_refunds_unified()` and reused in statement/dashboard totals.
- `python manage.py check` is passing after all changes.

Pending only environment execution:
- Run DB migration on production/cPanel.
- Run app tests where DB is reachable.

Known local limitation:
- Tests are blocked locally when MySQL is down (`WinError 10061`), so full suite pass must be validated on cPanel/server DB.
