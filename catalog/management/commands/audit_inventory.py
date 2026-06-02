from django.core.management.base import BaseCommand
from django.db.models import Sum

from catalog.models import Product
from catalog.models_stock import PrintRun, StockLedger, Warehouse   # ← YEHI LINE SAHI HAI


class Command(BaseCommand):
    help = "Audit inventory consistency (ledger is single source of truth)."

    def handle(self, *args, **options):
        self.stdout.write("Running inventory audit...\n")

        # -------------------------------
        # 1) Product-wise check
        # -------------------------------
        hard_mismatches = 0
        self.stdout.write("1) Product-wise on-hand check:\n")

        for p in Product.objects.all().order_by("sku"):
            # ledger truth
            agg = StockLedger.objects.filter(product=p).aggregate(
                total_in=Sum("in_qty"),
                total_out=Sum("out_qty"),
            )
            ledger_onhand = max(0, int((agg["total_in"] or 0) - (agg["total_out"] or 0)))

            # method (Product.available_stock)
            method_onhand = p.available_stock()

            # batches = sum of per-batch available_qty
            batch_total = 0
            for pr in p.print_runs.all():  # ← ye reverse relation kaam karega
                batch_total += pr.available_qty()

            line = (
                f"  SKU={p.sku.ljust(15)} | {str(p.name)[:30]:<30} | "
                f"ledger={ledger_onhand:<4} | method={method_onhand:<4} | batches={batch_total:<4}"
            )

            ok = True
            note = ""

            if method_onhand != ledger_onhand:
                ok = False
                hard_mismatches += 1
                note += " | method != ledger"

            unbatched_diff = ledger_onhand - batch_total
            if unbatched_diff != 0:
                note += f" | unbatched_diff={unbatched_diff}"

            status = "✔" if ok else "✖"
            self.stdout.write(line + note + f" | {status}")

        if hard_mismatches:
            self.stdout.write(f"\nProduct-level HARD mismatches: {hard_mismatches}\n")
        else:
            self.stdout.write("\nAll products: available_stock() matches ledger\n")

        # -------------------------------
        # 2) Warehouse-wise check
        # -------------------------------
        self.stdout.write("\n2) Warehouse-wise stock check:\n")
        for wh in Warehouse.objects.all().order_by("name"):
            agg_wh = StockLedger.objects.filter(warehouse=wh).aggregate(
                total_in=Sum("in_qty"),
                total_out=Sum("out_qty"),
            )
            wh_onhand = max(0, int((agg_wh["total_in"] or 0) - (agg_wh["total_out"] or 0)))

            # sum product-wise in this warehouse
            per_product_total = 0
            for p in Product.objects.filter(stock_ledgers__warehouse=wh).distinct():
                per_product_total += p.available_stock()  # ya direct ledger se bhi

            mark = "✔" if per_product_total == wh_onhand else "✖"
            self.stdout.write(
                f"  {wh.name:<20} | onhand={wh_onhand:<4} | sum_products={per_product_total:<4} | {mark}"
            )

        self.stdout.write("\nAudit finished.\n")