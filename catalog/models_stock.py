# catalog/models_stock.py
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


# ===========================
# Warehouse
# ===========================
class Warehouse(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    manager_name = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    opening_hours = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name


# ===========================
# PrintRun (Batches)
# ===========================
class PrintRun(models.Model):
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="print_runs",
    )
    batch_no = models.CharField(max_length=120, blank=True, null=True)
    printed_qty = models.PositiveIntegerField(default=0)
    received_qty = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    print_date = models.DateField(default=timezone.now)
    warehouse = models.ForeignKey(
        "catalog.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["print_date", "id"]
        indexes = [
            models.Index(fields=["product", "warehouse"]),
        ]

    def __str__(self):
        bn = self.batch_no or f"PR-{self.id}"
        sku = self.product.sku if self.product else "?"
        return f"{sku} | {bn} | {self.received_qty}/{self.printed_qty}"

    # 👇 YE METHOD FINAL VERSION HAI
    def available_qty(self):
        """
        Per-batch stock bhi ledger se niklega:
        sum(in_qty - out_qty) for this print_run.
        received_qty sirf informational hai.
        """
        from .models_stock import StockLedger
        agg = StockLedger.objects.filter(print_run=self).aggregate(
            total_in=models.Sum("in_qty"),
            total_out=models.Sum("out_qty"),
        )
        total_in = int(agg["total_in"] or 0)
        total_out = int(agg["total_out"] or 0)
        onhand = total_in - total_out
        return max(0, onhand)

# ===========================
# StockLedger (History Ledger)
# ===========================
class StockLedger(models.Model):
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='stock_ledgers'
    )
    print_run = models.ForeignKey(
        PrintRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    date = models.DateTimeField(auto_now_add=True)

    in_qty = models.IntegerField(default=0)
    out_qty = models.IntegerField(default=0)

    # Real-time balance stored for fast querying
    balance = models.IntegerField(default=0)

    ref_type = models.CharField(max_length=50)  # invoice, grn, adjustment, transfer
    ref_id = models.IntegerField(null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='stock_ledger_entries'
    )

    class Meta:
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['product', 'warehouse', 'date']),
            models.Index(fields=['ref_type', 'ref_id']),  # FAST REVERSAL LOOKUP
        ]

    def __str__(self):
        sku = self.product.sku if self.product else ""
        return f"{sku} | +{self.in_qty} -{self.out_qty} = {self.balance} @ {self.date.date()}"


# ======================================================
# ADVANCED STOCK FUNCTIONS
# ======================================================

def allocate_stock(product, qty, warehouse=None, ref_type='invoice', ref_id=None, notes=None, user=None):
    """
    FIFO allocation with update of ledger and returning allocation summary.
    This is transactional, atomic and ledger-safe.
    """
    from .models_stock import PrintRun, StockLedger

    qty = int(qty)
    if qty <= 0:
        return []

    allocations = []

    with transaction.atomic():

        prs = PrintRun.objects.select_for_update().filter(
            product=product
        ).order_by('print_date', 'id')

        remaining = qty

        for pr in prs:
            if remaining <= 0:
                break

            avail = pr.available_qty()
            if avail <= 0:
                continue

            take = min(avail, remaining)

            last = StockLedger.objects.filter(
                product=product,
                warehouse=warehouse
            ).order_by('-id').first()

            new_balance = (last.balance if last else 0) - take

            sl = StockLedger.objects.create(
                product=product,
                print_run=pr,
                warehouse=warehouse,
                in_qty=0,
                out_qty=take,
                balance=new_balance,
                ref_type=ref_type,
                ref_id=ref_id,
                notes=notes or f"Allocated {take} from {pr}",
                created_by=user
            )

            allocations.append({
                'print_run': pr,
                'qty': take,
                'ledger': sl
            })

            remaining -= take

        if remaining > 0:
            raise ValueError(
                f"Not enough stock for {product.sku}. Needed: {qty}, Available: {qty-remaining}"
            )

    return allocations


def add_stock_via_pr(print_run, received_qty, user=None):
    """
    Record inbound stock from a PrintRun (Goods Receipt)
    """
    from .models_stock import StockLedger

    prev = StockLedger.objects.filter(
        product=print_run.product,
        warehouse=print_run.warehouse
    ).order_by('-id').first()

    new_balance = (prev.balance if prev else 0) + received_qty

    return StockLedger.objects.create(
        product=print_run.product,
        print_run=print_run,
        warehouse=print_run.warehouse,
        in_qty=received_qty,
        out_qty=0,
        balance=new_balance,
        ref_type="pr_receive",
        ref_id=print_run.id,
        notes=f"PrintRun received",
        created_by=user
    )
