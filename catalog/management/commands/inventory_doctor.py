# catalog/management/commands/inventory_doctor.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction

from catalog.models import Product
from catalog.models_stock import StockLedger, PrintRun, Warehouse


class Command(BaseCommand):
    help = "Inventory Doctor – diagnose and optionally FIX safe inventory issues."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Apply safe fixes instead of dry-run only.",
        )

    def handle(self, *args, **options):
        do_fix = options.get("fix", False)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nINVENTORY DOCTOR – LEDGER HEALTH & AUTO-FIX\n"
        ))
        if do_fix:
            self.stdout.write(self.style.WARNING("RUNNING IN FIX MODE (changes will be written)\n"))
        else:
            self.stdout.write(self.style.SUCCESS("DRY RUN ONLY (no changes will be written)\n"))

        # ------------------------------------------------------------------
        # STEP 0 – Pre-check: run full_inventory_health_check (for context)
        # ------------------------------------------------------------------
        self.stdout.write(self.style.HTTP_INFO("STEP 0 → Current health status (before fixes):"))
        try:
            call_command("full_inventory_health_check")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f"  full_inventory_health_check could not be executed: {exc}"
            ))

        # ------------------------------------------------------------------
        # STEP 1 – Rebuild StockLedger.balance per product+warehouse
        # ------------------------------------------------------------------
        self.stdout.write(self.style.HTTP_INFO("\nSTEP 1 → Rebuild StockLedger.balance (running balance)\n"))

        # All ledger entries ordered by logical sequence
        ledgers = (
            StockLedger.objects
            .select_related("product", "warehouse")
            .order_by("product_id", "warehouse_id", "date", "id")
        )

        changed_balances = 0
        total_entries = ledgers.count()

        def key_fn(sl):
            return (sl.product_id, sl.warehouse_id)

        current_key = None
        running_balance = 0

        with transaction.atomic():
            for sl in ledgers:
                key = key_fn(sl)

                # New product+warehouse group → reset running balance
                if key != current_key:
                    current_key = key
                    running_balance = 0

                delta = int(sl.in_qty or 0) - int(sl.out_qty or 0)
                expected_balance = running_balance + delta

                if sl.balance != expected_balance:
                    if do_fix:
                        sl.balance = expected_balance
                        sl.save(update_fields=["balance"])
                    changed_balances += 1

                running_balance = expected_balance

            if not do_fix:
                # Dry-run: rollback automatically at end of atomic block,
                # but we explicitly say we are NOT committing.
                self.stdout.write(self.style.WARNING(
                    "  DRY RUN: balance changes were NOT saved."
                ))

        self.stdout.write(
            f"  Processed {total_entries} ledger entries, "
            f"{changed_balances} would be updated.\n"
        )

        # ------------------------------------------------------------------
        # STEP 2 – Fix obvious orphan fields on StockLedger
        #          (product / warehouse null but inferable from PrintRun)
        # ------------------------------------------------------------------
        self.stdout.write(self.style.HTTP_INFO("STEP 2 → Fix orphan ledger fields from PrintRun\n"))

        qs = StockLedger.objects.select_related("print_run", "product", "warehouse")
        fixed_product = 0
        fixed_warehouse = 0

        with transaction.atomic():
            for sl in qs:
                updated = False

                # If product is NULL but print_run has a product
                if sl.product_id is None and sl.print_run and sl.print_run.product_id:
                    sl.product = sl.print_run.product
                    fixed_product += 1
                    updated = True

                # If warehouse is NULL but print_run has a warehouse
                if sl.warehouse_id is None and sl.print_run and sl.print_run.warehouse_id:
                    sl.warehouse = sl.print_run.warehouse
                    fixed_warehouse += 1
                    updated = True

                if updated and do_fix:
                    sl.save(update_fields=["product", "warehouse"])

            if not do_fix:
                self.stdout.write(self.style.WARNING(
                    "  DRY RUN: orphan fixes were NOT saved."
                ))

        self.stdout.write(
            f"  Product fixed (from PrintRun): {fixed_product}\n"
            f"  Warehouse fixed (from PrintRun): {fixed_warehouse}\n"
        )

        # ------------------------------------------------------------------
        # STEP 3 – Summary + post-check
        # ------------------------------------------------------------------
        self.stdout.write(self.style.SQL_TABLE("\nSUMMARY"))
        if do_fix:
            self.stdout.write(self.style.SUCCESS(
                f"  Fix mode complete. balance_fixed={changed_balances}, "
                f"product_fixed={fixed_product}, warehouse_fixed={fixed_warehouse}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"  Dry-run complete. If this looks correct, run again with --fix."
            ))

        self.stdout.write(self.style.HTTP_INFO(
            "\nSTEP 4 → Health status AFTER fixes (simulated if dry run):\n"
        ))
        try:
            call_command("full_inventory_health_check")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f"  full_inventory_health_check (post) could not be executed: {exc}"
            ))

        self.stdout.write("\n" + "=" * 70)
        if do_fix:
            self.stdout.write(self.style.SUCCESS("   INVENTORY DOCTOR COMPLETED IN FIX MODE   "))
        else:
            self.stdout.write(self.style.WARNING("   INVENTORY DOCTOR COMPLETED IN DRY-RUN MODE   "))
        self.stdout.write("=" * 70 + "\n")

