# catalog/management/commands/seed_legacy_stock.py
from django.core.management.base import BaseCommand
from catalog.models import Product
from catalog.models_stock import Warehouse, PrintRun, StockLedger
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = "Seed legacy stock: create a PrintRun per product representing current stock."

    def add_arguments(self, parser):
        parser.add_argument('--warehouse', help='Warehouse name to assign (optional)', default=None)

    def handle(self, *args, **options):
        warehouse_name = options.get('warehouse')
        wh = None
        if warehouse_name:
            wh, _ = Warehouse.objects.get_or_create(name=warehouse_name)

        products = Product.objects.all()
        created = 0
        for p in products:
            # attempt to get existing stock number from Product.available_stock() if available
            stock = None
            try:
                stock = p.available_stock()
            except Exception:
                stock = None

            # fallback: ask user to set stock manually (skip if None or zero)
            if stock is None:
                continue
            if stock <= 0:
                continue

            pr = PrintRun.objects.create(
                product=p,
                batch_no=f"legacy-{p.sku}",
                printed_qty=stock,
                received_qty=stock,
                unit_cost=Decimal('0.00'),
                print_date=timezone.now().date(),
                warehouse=wh
            )
            # create ledger in row
            StockLedger.objects.create(
                product=p,
                print_run=pr,
                warehouse=wh,
                in_qty=stock,
                out_qty=0,
                balance=stock,
                ref_type='legacy_seed',
                ref_id=pr.id,
                notes='Legacy seed import'
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} legacy print runs / stock entries."))
