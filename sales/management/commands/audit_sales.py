# sales/management/commands/audit_sales.py

from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal

from sales.models import Invoice, InvoiceItem, Payment, Customer
from catalog.models_stock import StockLedger
from catalog.models import Product as CatalogProduct


class Command(BaseCommand):
    help = "Audit SALES + INVENTORY integration: invoices vs StockLedger vs payments vs customers"

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("        SALES + INVENTORY HEALTH CHECK – PRODUCTION AUDIT")
        self.stdout.write("=" * 70)
        self.stdout.write("")

        self._check_invoice_stock_links()
        self._check_deleted_and_bin_invoices()
        self._check_payments_vs_invoice_fields()
        self._check_customer_balances()

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("   SALES AUDIT COMPLETE – See above for any mismatches")
        self.stdout.write("=" * 70)
        self.stdout.write("")

    # -------------------------------------------------------
    # 1) Invoice items vs StockLedger (ref_type='invoice')
    # -------------------------------------------------------
    def _check_invoice_stock_links(self):
        self.stdout.write("1) INVOICE ITEMS vs STOCK LEDGER (ref_type='invoice')\n")

        ok_count = 0
        mismatch_count = 0

        invoices = (
            Invoice.objects.filter(in_bin=False)
            .prefetch_related("items")
        )

        for inv in invoices:
            # product-wise quantity on invoice (only track_stock products)
            item_sums = (
                InvoiceItem.objects.filter(invoice=inv, product__isnull=False, product__track_stock=True)
                .values("product_id")
                .annotate(qty=Sum("quantity"))
            )

            for row in item_sums:
                pid = row["product_id"]
                qty_on_invoice = int(row["qty"] or 0)

                # total OUT in ledger for this invoice & product
                led_out = (
                    StockLedger.objects.filter(
                        ref_type="invoice",
                        ref_id=inv.id,
                        product_id=pid,
                    ).aggregate(total=Sum("out_qty"))["total"]
                    or 0
                )
                led_out = int(led_out)

                if qty_on_invoice != led_out:
                    mismatch_count += 1
                    prod = CatalogProduct.objects.filter(id=pid).first()
                    sku = prod.sku if prod else "-"
                    name = prod.name if prod else "-"
                    self.stdout.write(
                        f"  [MISMATCH] Invoice {inv.number} | {sku} - {name} | "
                        f"Items={qty_on_invoice} vs Ledger OUT={led_out}"
                    )
                else:
                    ok_count += 1

        if mismatch_count == 0:
            self.stdout.write(f"  ✔ All invoice → StockLedger links correct ({ok_count} product-lines)")
        self.stdout.write("")

    # -------------------------------------------------------
    # 2) Deleted / Bin invoices consistency
    # -------------------------------------------------------
    def _check_deleted_and_bin_invoices(self):
        self.stdout.write("2) BIN / DELETED INVOICES vs LEDGER\n")

        # Invoices in bin: ideally, unallocated (stock reversed)
        bin_invoices = Invoice.objects.filter(in_bin=True)
        prob = 0

        for inv in bin_invoices:
            out_sum = (
                StockLedger.objects.filter(ref_type="invoice", ref_id=inv.id)
                .aggregate(total=Sum("out_qty"))["total"]
                or 0
            )
            out_sum = int(out_sum)
            if out_sum != 0:
                prob += 1
                self.stdout.write(
                    f"  [WARN] Invoice {inv.number} is in BIN but has OUT entries: {out_sum}"
                )

        if prob == 0:
            self.stdout.write("  ✔ All BIN invoices have no active OUT allocations")
        self.stdout.write("")

    # -------------------------------------------------------
    # 3) Payments vs Invoice paid_amount / balance_due
    # -------------------------------------------------------
    def _check_payments_vs_invoice_fields(self):
        self.stdout.write("3) PAYMENTS vs INVOICE paid_amount / balance_due\n")

        mismatch = 0
        ok = 0

        for inv in Invoice.objects.all():
            # Simple, clear version:
            paid_sum = (
                Payment.objects.filter(invoice=inv, is_refund=False)
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            refund_sum = (
                Payment.objects.filter(invoice=inv, is_refund=True)
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            net_received = (paid_sum - refund_sum).quantize(Decimal("0.01"))
            expected_balance = (inv.grand_total - net_received).quantize(Decimal("0.01"))

            paid_field = (inv.paid_amount or Decimal("0.00")).quantize(Decimal("0.01"))
            balance_field = (inv.balance_due or Decimal("0.00")).quantize(Decimal("0.01"))

            if paid_field != net_received or balance_field != expected_balance:
                mismatch += 1
                self.stdout.write(
                    f"  [MISMATCH] Invoice {inv.number} | "
                    f"paid_amount={paid_field} vs NET={net_received} | "
                    f"balance_due={balance_field} vs expected={expected_balance}"
                )
            else:
                ok += 1

        if mismatch == 0:
            self.stdout.write(f"  ✔ All invoices match payments/refunds ({ok} invoices)")
        self.stdout.write("")

    # -------------------------------------------------------
    # 4) Customer total_spent / pending_balance
    # -------------------------------------------------------
    def _check_customer_balances(self):
        self.stdout.write("4) CUSTOMER BALANCES (total_spent / pending_balance)\n")

        mismatch = 0
        ok = 0

        for cust in Customer.objects.all():
            agg = cust.invoices.aggregate(
                total=Sum("grand_total"),
                paid=Sum("paid_amount"),
            )
            total = (agg["total"] or Decimal("0.00")).quantize(Decimal("0.01"))
            paid = (agg["paid"] or Decimal("0.00")).quantize(Decimal("0.01"))
            pending = (total - paid).quantize(Decimal("0.01"))

            ts_field = (cust.total_spent or Decimal("0.00")).quantize(Decimal("0.01"))
            pb_field = (cust.pending_balance or Decimal("0.00")).quantize(Decimal("0.01"))

            if ts_field != total or pb_field != pending:
                mismatch += 1
                self.stdout.write(
                    f"  [MISMATCH] Customer {cust.name} | "
                    f"total_spent={ts_field} vs {total} | "
                    f"pending_balance={pb_field} vs {pending}"
                )
            else:
                ok += 1

        if mismatch == 0:
            self.stdout.write(f"  ✔ All customers balances correct ({ok} customers)")
        self.stdout.write("")

