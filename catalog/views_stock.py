# catalog/views_stock.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from django.db import transaction

from django.apps import apps
from django.db.models import Sum

# IMPORT SERVICE LAYER
from .inventory_utils import (
    allocate_fifo_preview,
    allocate_and_commit,
    reverse_allocation,
    adjust_stock,
    product_stock_snapshot,
)

# MODEL RESOLUTION
Product = apps.get_model('catalog', 'Product')
PrintRun = apps.get_model('catalog', 'PrintRun')
StockLedger = apps.get_model('catalog', 'StockLedger')
Warehouse = apps.get_model('catalog', 'Warehouse')


# ======================================================
# STAFF CHECK
# ======================================================

def staff_required(user):
    return user.is_active and (user.is_staff or user.is_superuser)


# ======================================================
# PRODUCT STOCK PAGE
# ======================================================

@login_required
@user_passes_test(staff_required)
def product_stock(request):
    """
    Shows stock for every product with simple on-hand calculation.
    """
    products = Product.objects.all().order_by("name")

    results = []
    for p in products:

        agg = StockLedger.objects.filter(product=p).aggregate(
            total_in=Sum("in_qty"),
            total_out=Sum("out_qty"),
        )
        onhand = (agg["total_in"] or 0) - (agg["total_out"] or 0)

        results.append({
            "product": p,
            "onhand": onhand,
            "sku": p.sku,
            "price": p.price,
        })

    return render(request, "catalog/product_stock.html", {"results": results})


# ======================================================
# PRINT RUN DETAIL VIEW
# ======================================================

@login_required
@user_passes_test(staff_required)
def pr_detail(request, pk):
    pr = get_object_or_404(PrintRun, pk=pk)

    leds = StockLedger.objects.filter(print_run=pr).order_by("-date", "-id")

    return render(request, "catalog/printrun_detail.html", {
        "pr": pr,
        "ledgers": leds
    })


# ======================================================
# WAREHOUSE DETAIL VIEW
# ======================================================

@login_required
@user_passes_test(staff_required)
def warehouse_detail(request, pk):
    w = get_object_or_404(Warehouse, pk=pk)

    leds = StockLedger.objects.filter(warehouse=w).order_by("-date", "-id")

    return render(request, "catalog/warehouse_detail.html", {
        "warehouse": w,
        "ledgers": leds
    })


# ======================================================
# API — Allocation PREVIEW
# ======================================================

@login_required
@user_passes_test(staff_required)
def api_allocate_preview(request, pk):
    """
    API — returns FIFO allocation preview (no DB write)
    """
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    qty = request.GET.get("qty", 0)

    try:
        qty = int(qty)
    except:
        return JsonResponse({"error": "Invalid qty"}, status=400)

    plan = allocate_fifo_preview(product, qty)
    if plan is None:
        return JsonResponse({
            "ok": False,
            "insufficient": True,
            "message": "Insufficient stock"
        })

    # JSON SERIAL
    serial = []
    for p in plan:
        serial.append({
            "print_run_id": p["print_run"].id,
            "batch_no": p["batch_no"],
            "qty": p["qty"],
            "available": p["available"],
            "warehouse": p["warehouse"],
            "print_date": p["date"].isoformat(),
        })

    return JsonResponse({
        "ok": True,
        "insufficient": False,
        "allocated": serial,
    })


# ======================================================
# API — Allocation COMMIT
# ======================================================

@login_required
@user_passes_test(staff_required)
@transaction.atomic
def api_allocate_commit(request):
    """
    POST => product_id, qty, ref_type, ref_id
    Creates ledger entries
    """
    try:
        product_id = int(request.POST.get("product_id"))
        qty = int(request.POST.get("qty"))
        ref_type = request.POST.get("ref_type", "invoice")
        ref_id = int(request.POST.get("ref_id", 0))
    except:
        return JsonResponse({"error": "Invalid input"}, status=400)

    try:
        product = Product.objects.get(pk=product_id)
    except:
        return JsonResponse({"error": "Product not found"}, status=404)

    try:
        sl_entries = allocate_and_commit(
            product=product,
            qty=qty,
            ref_type=ref_type,
            ref_id=ref_id,
            user=request.user,
        )
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

    return JsonResponse({
        "ok": True,
        "created": len(sl_entries),
        "message": "Stock allocated successfully",
    })


# ======================================================
# API — Reverse Allocation
# ======================================================

@login_required
@user_passes_test(staff_required)
@transaction.atomic
def api_reverse_allocation(request):
    """
    Reverse stock for a ref_type + ref_id
    """
    ref_type = request.POST.get("ref_type")
    ref_id = request.POST.get("ref_id")

    if not ref_type or not ref_id:
        return JsonResponse({"error": "Missing ref_type or ref_id"}, status=400)

    sl = reverse_allocation(
        ref_type=ref_type,
        ref_id=ref_id,
        user=request.user
    )

    return JsonResponse({
        "ok": True,
        "reversed": len(sl),
        "message": "Reversal completed"
    })


# ======================================================
# API — Manual Adjustment
# ======================================================

@login_required
@user_passes_test(staff_required)
@transaction.atomic
def api_adjust_stock(request):
    """
    POST => product_id, qty (+ or -)
    """
    try:
        product_id = int(request.POST.get("product_id"))
        qty = int(request.POST.get("qty"))
    except:
        return JsonResponse({"error": "Invalid input"}, status=400)

    product = Product.objects.get(pk=product_id)

    sl = adjust_stock(
        product=product,
        qty=qty,
        user=request.user,
        reason=f"Manual adjustment by {request.user}",
    )

    return JsonResponse({
        "ok": True,
        "entry_id": sl.id,
        "message": "Adjustment saved"
    })
