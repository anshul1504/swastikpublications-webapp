# catalog/inventory_utils.py
"""
Enterprise-level stock allocator and ledger service.

This module provides:
- FIFO preview (no DB write)
- FIFO allocation + commit (DB write)
- Reverse allocation (returns stock)
- Manual adjustment
- Product stock snapshot

Backward compatibility:
- allocate_fifo()
- commit_allocation()
- reverse_allocation_for_invoice()
"""

from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

# Model imports
from .models_stock import PrintRun, StockLedger, Warehouse
from .models import Product


# =====================================================================
# INTERNAL SAFETY HELPERS
# =====================================================================

def _get_last_balance(product, warehouse=None):
    """Return latest ledger balance for product & warehouse."""
    last = StockLedger.objects.filter(
        product=product,
        warehouse=warehouse
    ).order_by("-id").first()
    return int(last.balance) if last and last.balance is not None else 0


def _safe_available(pr):
    """Return available stock on a PrintRun safely."""
    try:
        return int(pr.available_qty())
    except Exception:
        out = StockLedger.objects.filter(print_run=pr).aggregate(
            t=Sum("out_qty")
        )["t"] or 0
        recv = int(pr.received_qty or 0)
        return max(0, recv - out)


# =====================================================================
# 1) FIFO PREVIEW — no DB write
# =====================================================================

def allocate_fifo_preview(product, qty_needed):
    """Return list of possible allocations WITHOUT writing to DB."""
    qty_left = int(qty_needed or 0)
    plan = []

    prs = PrintRun.objects.filter(product=product).order_by("print_date", "id")

    for pr in prs:
        if qty_left <= 0:
            break

        avail = _safe_available(pr)
        if avail <= 0:
            continue

        take = min(avail, qty_left)

        plan.append({
            "print_run": pr,
            "qty": take,
            "available": avail,
            "batch_no": pr.batch_no,
            "warehouse": pr.warehouse.name if pr.warehouse else None,
            "date": pr.print_date,
        })

        qty_left -= take

    return None if qty_left > 0 else plan


# =====================================================================
# 2) FIFO COMMIT — DB write (enterprise + safe)
# =====================================================================

@transaction.atomic
def allocate_and_commit(product, qty, ref_type="invoice", ref_id=None, user=None, notes=None, warehouse=None):
    """
    HARD allocation — subtracts stock from FIFO runs and writes StockLedger.
    """
    qty = int(qty or 0)
    if qty <= 0:
        return []

    created = []
    remaining = qty

    prs = PrintRun.objects.select_for_update().filter(
        product=product
    ).order_by("print_date", "id")

    for pr in prs:
        if remaining <= 0:
            break

        avail = _safe_available(pr)
        if avail <= 0:
            continue

        take = min(avail, remaining)

        new_balance = _get_last_balance(product, warehouse) - take

        entry = {
            "product": product,
            "print_run": pr,
            "warehouse": warehouse or pr.warehouse,
            "in_qty": 0,
            "out_qty": take,
            "balance": new_balance,
            "ref_type": ref_type,
            "ref_id": ref_id,
            "notes": notes or f"Allocated {take} units",
        }

        # optional user safety
        if hasattr(StockLedger, "created_by"):
            entry["created_by"] = user

        sl = StockLedger.objects.create(**entry)

        created.append(sl)
        remaining -= take

    if remaining > 0:
        raise ValueError(f"Insufficient stock. Needed {qty}, allocated {qty-remaining}")

    return created


# =====================================================================
# 3) REVERSE ALLOCATION — DB write (idempotent & safe)
# =====================================================================

@transaction.atomic
def reverse_allocation(ref_type, ref_id, user=None, notes=None):
    """
    Create IN entries to reverse previous allocations for a given ref.

    Strategy:
    - Pehle jitne bhi <ref_type>_reverse rows hain, unhe delete kar do
      (full reset for this invoice / ref).
    - Fir saare OUT rows (ref_type=ref_type, ref_id=ref_id) ke against
      full qty ka IN create karo.
    - Isse har call pe net effect ye hoga ki poora allocation reverse ho
      jaata hai, chahe kitni baar call karo (idempotent at invoice-level).
    """
    created = []

    # 0) Clear any previous reverse rows for this ref
    StockLedger.objects.filter(
        ref_type=f"{ref_type}_reverse",
        ref_id=ref_id,
    ).delete()

    # 1) Fetch all OUT rows for this ref
    rows = StockLedger.objects.filter(ref_type=ref_type, ref_id=ref_id).order_by("id")

    for old in rows:
        qty_out = int(old.out_qty or 0)
        if qty_out <= 0:
            continue

        # Hamesha full qty_out reverse karo
        remaining = qty_out

        new_balance = _get_last_balance(old.product, old.warehouse) + remaining

        entry = {
            "product": old.product,
            "print_run": old.print_run,
            "warehouse": old.warehouse,
            "in_qty": remaining,
            "out_qty": 0,
            "balance": new_balance,
            "ref_type": f"{ref_type}_reverse",
            "ref_id": old.ref_id,
            "notes": notes or "Reverse allocation",
        }
        if hasattr(StockLedger, "created_by"):
            entry["created_by"] = user

        created.append(StockLedger.objects.create(**entry))

    return created

# =====================================================================
# 4) MANUAL ADJUSTMENT
# =====================================================================

@transaction.atomic
def adjust_stock(product, qty, warehouse=None, user=None, reason="Manual adjustment"):
    """Manually add or remove stock."""
    qty = int(qty or 0)
    prev = _get_last_balance(product, warehouse)
    new_balance = prev + qty

    entry = {
        "product": product,
        "warehouse": warehouse,
        "in_qty": qty if qty > 0 else 0,
        "out_qty": abs(qty) if qty < 0 else 0,
        "balance": new_balance,
        "ref_type": "adjustment",
        "ref_id": None,
        "notes": reason,
    }
    if hasattr(StockLedger, "created_by"):
        entry["created_by"] = user

    return StockLedger.objects.create(**entry)


# =====================================================================
# 5) STOCK SNAPSHOT
# =====================================================================

def product_stock_snapshot(product):
    """Return total onhand for API."""
    agg = StockLedger.objects.filter(product=product).aggregate(
        tin=Sum("in_qty"), tout=Sum("out_qty")
    )
    tin = agg["tin"] or 0
    tout = agg["tout"] or 0
    return {
        "product": product.id,
        "sku": getattr(product, "sku", ""),
        "name": getattr(product, "name", ""),
        "onhand": int(tin - tout),
    }


# =====================================================================
# BACKWARD COMPATIBILITY (old imports won't break)
# =====================================================================

def allocate_fifo(product, qty_needed):
    """Legacy name — maps to preview only."""
    preview = allocate_fifo_preview(product, qty_needed)
    if preview is None:
        return None
    return [(p["print_run"], p["qty"]) for p in preview]


def commit_allocation(invoice, invoice_item, allocations, ref_type="invoice"):
    """Legacy name for commit."""
    created = []
    for pr, qty in allocations:
        created.extend(
            allocate_and_commit(
                product=invoice_item.product,
                qty=qty,
                ref_type=ref_type,
                ref_id=invoice.id,
                warehouse=pr.warehouse,
                notes=f"Legacy commit for invoice {invoice.id}",
            )
        )
    return created


def reverse_allocation_for_invoice(invoice, ref_type="invoice"):
    """Legacy name for reverse."""
    return reverse_allocation(ref_type, invoice.id)


# catalog/inventory_utils.py

from django.db import transaction

def allocate_invoice(inv):
    """
    Hard reset stock allocation for a single invoice.

    Steps:
    - Remove ALL previous StockLedger rows for this invoice (ref_type='invoice' / 'invoice_reverse')
    - For each invoice item that has a real product and positive quantity:
        - Use allocate_fifo_preview() to get batch-wise allocation
        - Convert preview dicts -> (PrintRun, qty) tuples
        - Commit allocation via commit_allocation()
    """

    from catalog.models_stock import StockLedger  # local import to avoid cycles
    from catalog.inventory_utils import allocate_fifo_preview, commit_allocation

    with transaction.atomic():
        # 1) Purani saari allocations clean sweep
        StockLedger.objects.filter(
            ref_id=inv.id,
            ref_type__in=["invoice", "invoice_reverse"],
        ).delete()

        # 2) Fresh allocation for each line item
        for item in inv.items.all():
            # Manual description / service lines ya zero / negative qty skip
            if not item.product_id or not item.quantity or item.quantity <= 0:
                continue

            preview = allocate_fifo_preview(item.product, item.quantity)
            # preview = list of dicts: {"print_run": PR, "qty": x, ...}

            allocations = [
                (alloc["print_run"], alloc["qty"])
                for alloc in preview
                if alloc.get("qty", 0) > 0
            ]

            if allocations:
                commit_allocation(inv, item, allocations)
