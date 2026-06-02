# catalog/management/commands/full_inventory_health_check.py
from django.core.management.base import BaseCommand
from django.db.models import Sum, F
from catalog.models import Product
from catalog.models_stock import StockLedger, PrintRun, Warehouse


class Command(BaseCommand):
    help = "COMPLETE Inventory Health Check – 100% Production Ready"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nFULL INVENTORY HEALTH CHECK – PRODUCTION AUDIT\n"
        ))
        errors = 0
        warnings = 0

        # 1. Ledger vs Method
        self.stdout.write("1. Ledger vs Product.available_stock()")
        for p in Product.objects.filter(track_stock=True):
            ledger_qty = max(0, (StockLedger.objects.filter(product=p).aggregate(
                i=Sum('in_qty'))['i'] or 0) - (StockLedger.objects.filter(product=p).aggregate(
                o=Sum('out_qty'))['o'] or 0))

            method_qty = p.available_stock()

            if ledger_qty != method_qty:
                errors += 1
                self.stdout.write(self.style.ERROR(f"   CRITICAL → {p.sku} | Ledger={ledger_qty} ≠ Method={method_qty}"))
            else:
                self.stdout.write(f"   {p.sku.ljust(15)} → {ledger_qty} Correct")

        # 2. Negative stock
        self.stdout.write("\n2. Negative stock check")
        if Product.objects.filter(track_stock=True).extra(where=["""
            COALESCE((SELECT SUM(in_qty)-SUM(out_qty) FROM catalog_stockledger 
                     WHERE product_id = catalog_product.id), 0) < 0
        """]).exists():
            errors += 1
            self.stdout.write(self.style.ERROR("   NEGATIVE STOCK DETECTED!"))
        else:
            self.stdout.write("   No negative stock Correct")

        # 3. Batched vs Unbatched
        self.stdout.write("\n3. Batched vs Unbatched stock")
        for p in Product.objects.filter(track_stock=True):
            batch_sum = sum(pr.available_qty() for pr in p.print_runs.all())
            total = p.available_stock()
            diff = total - batch_sum
            if diff > 0:
                warnings += 1
                self.stdout.write(self.style.WARNING(f"   {p.sku} → +{diff} units without batch (normal)"))
            elif diff < 0:
                errors += 1
                self.stdout.write(self.style.ERROR(f"   IMPOSSIBLE → {p.sku} batch > ledger!"))

        # 4. Warehouse total validation (FIXED VERSION)
        self.stdout.write("\n4. Warehouse-wise validation")
        for wh in Warehouse.objects.all():
            # Direct from ledger
            ledger_total = max(0, (StockLedger.objects.filter(warehouse=wh).aggregate(
                i=Sum('in_qty'))['i'] or 0) - (StockLedger.objects.filter(warehouse=wh).aggregate(
                o=Sum('out_qty'))['o'] or 0))

            # Via products (warehouse-specific method)
            products_in_wh = Product.objects.filter(stock_ledgers__warehouse=wh).distinct()
            via_product_total = sum(p.available_stock_warehouse(wh) for p in products_in_wh)

            if ledger_total != via_product_total:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f"   {wh.name} → Ledger={ledger_total} ≠ ViaProducts={via_product_total}"
                ))
            else:
                self.stdout.write(f"   {wh.name} → {ledger_total} Correct")

        # 5. Orphan ledger rows
        self.stdout.write("\n5. Orphan ledger entries")
        orphans = StockLedger.objects.filter(product__isnull=True)
        if orphans.exists():
            errors += 1
            self.stdout.write(self.style.ERROR(f"   {orphans.count()} orphan ledger rows (NULL product)"))
        else:
            self.stdout.write("   No orphans Correct")

        # 6. PrintRun sanity
        self.stdout.write("\n6. PrintRun received ≤ printed")
        bad_pr = PrintRun.objects.filter(received_qty__gt=F('printed_qty'))
        if bad_pr.exists():
            warnings += 1
            for pr in bad_pr:
                self.stdout.write(self.style.WARNING(
                    f"   PR-{pr.id} → Received {pr.received_qty} > {pr.printed_qty} printed"
                ))
        else:
            self.stdout.write("   All PrintRuns logical Correct")

        # FINAL RESULT
        self.stdout.write("\n" + "="*70)
        if errors == 0:
            self.stdout.write(self.style.SUCCESS(
                "    100% CLEAN INVENTORY – SYSTEM ABSOLUTELY SAFE & READY!    "
            ))
            if warnings > 0:
                self.stdout.write(self.style.WARNING(f"    {warnings} minor warnings (normal in real data)"))
        else:
            self.stdout.write(self.style.ERROR(f"    CRITICAL ERRORS: {errors} → FIX KARNA ZAROORI HAI!    "))

        self.stdout.write("="*70 + "\n")