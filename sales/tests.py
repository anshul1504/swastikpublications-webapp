# sales/tests.py

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from catalog.models import Product as CatalogProduct
from catalog.models_stock import Warehouse, PrintRun, StockLedger
from catalog.inventory_utils import allocate_and_commit
from sales.models import Customer, CompanyProfile, Invoice, InvoiceItem


User = get_user_model()


class InvoiceInventoryIntegrationTests(TestCase):
    """
    End-to-end tests to validate:
    - Invoice create allocates stock (StockLedger out_qty)
    - Invoice edit reverses old allocation and re-allocates fresh
    - Invoice delete restores stock
    """

    def setUp(self):
        # --- Auth client (very important because views use @login_required) ---
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,  # safe for tests
        )
        self.client.login(username="tester", password="testpass123")

        # --- Basic customer + company ---
        self.customer = Customer.objects.create(name="Test Customer")
        self.company = CompanyProfile.objects.create(
            name="Test Company",
            address="Indore",
        )

        # --- Warehouse + Product + initial stock ---
        self.wh = Warehouse.objects.create(name="Test WH")
        self.prod = CatalogProduct.objects.create(
            sku="TEST-01",
            name="Test Product",
            price=Decimal("100.00"),
            tax_rate=18,
            track_stock=True,
        )

        # 150 units stock via PrintRun + Ledger
        self.pr = PrintRun.objects.create(
            product=self.prod,
            printed_qty=150,
            received_qty=150,
            warehouse=self.wh,
            notes="Test stock",
        )

        StockLedger.objects.create(
            product=self.prod,
            print_run=self.pr,
            warehouse=self.wh,
            in_qty=150,
            out_qty=0,
            balance=150,
            ref_type="initial",
            ref_id=self.pr.id,
            notes="Initial test stock",
        )

        # Sanity check
        self.assertEqual(self.prod.available_stock(), 150)

    # ----------------- helpers -----------------

    def _create_invoice_via_view(self, qty: int) -> Invoice:
        """
        Helper: hit invoice_add view with single product line of given qty.
        """
        url = reverse("sales:invoice_add")
        today = timezone.localdate()

        post_data = {
            "number": "TEST-INV-1",
            "customer": str(self.customer.id),
            "company": str(self.company.id),
            "date": today.strftime("%Y-%m-%d"),
            "billing_address": "Addr",
            "shipping_address": "Addr",
            # single line arrays
            "product[]": [str(self.prod.id)],
            "manual_product[]": [""],
            "qty[]": [str(qty)],
            "rate[]": ["100"],
            "tax[]": ["18"],
            "discount[]": ["0"],
            # no payments initially
            "payment_amount[]": [""],
            "payment_method[]": [""],
            "payment_date[]": [""],
        }

        resp = self.client.post(url, post_data, follow=True)
        # If not logged in, this would be login page. We are logged in, so this should be invoice detail.
        self.assertEqual(resp.status_code, 200)

        inv = Invoice.objects.order_by("-id").first()
        self.assertIsNotNone(inv)
        return inv

    def _edit_invoice_qty(self, inv: Invoice, new_qty: int) -> Invoice:
        """
        Helper: POST to invoice_edit with updated qty for same product.
        """
        url = reverse("sales:invoice_edit", args=[inv.id])
        today = timezone.localdate()

        post_data = {
            "number": inv.number,
            "customer": str(self.customer.id),
            "company": str(self.company.id),
            "date": today.strftime("%Y-%m-%d"),
            "billing_address": "Addr",
            "shipping_address": "Addr",
            "notes": "",
            "terms": "",
            "bank_name": "",
            "bank_branch": "",
            "account_number": "",
            "ifsc": "",
            "upi": "",
            # one line only
            "product[]": [str(self.prod.id)],
            "manual_product[]": [""],
            "qty[]": [str(new_qty)],
            "rate[]": ["100"],
            "tax[]": ["18"],
            "discount[]": ["0"],
            # no payments for this test
            "payment_amount[]": [""],
            "payment_method[]": [""],
            "payment_date[]": [""],
        }

        resp = self.client.post(url, post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        inv.refresh_from_db()
        return inv

    # -------------------------------------------------
    # MAIN TEST: create -> edit -> edit -> delete
    # -------------------------------------------------
    def test_invoice_create_edit_delete_updates_stock(self):
        """
        Scenario:

        - Start: stock = 150
        - After create (qty 10) => should be 140
        - After edit (qty 20)   => should be 130
        - After edit (qty 5)    => should be 145
        - After delete          => should be back to 150
        """

        # Before
        self.assertEqual(self.prod.available_stock(), 150)

        # 1) CREATE (10 qty)
        inv = self._create_invoice_via_view(10)
        self.prod.refresh_from_db()
        after_create = self.prod.available_stock()
        self.assertEqual(
            after_create, 140,
            f"After create expected 140, got {after_create}",
        )

        # 2) EDIT to 20 qty
        inv = self._edit_invoice_qty(inv, 20)
        self.prod.refresh_from_db()
        after_edit_20 = self.prod.available_stock()
        self.assertEqual(
            after_edit_20, 130,
            f"After edit(20) expected 130, got {after_edit_20}",
        )

        # 3) EDIT to 5 qty
        inv = self._edit_invoice_qty(inv, 5)
        self.prod.refresh_from_db()
        after_edit_5 = self.prod.available_stock()
        self.assertEqual(
            after_edit_5, 145,
            f"After edit(5) expected 145, got {after_edit_5}",
        )

        # 4) DELETE invoice (permanent)
        url_delete = reverse("sales:invoice_delete", args=[inv.id])
        resp = self.client.post(url_delete, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.prod.refresh_from_db()
        after_delete = self.prod.available_stock()
        self.assertEqual(
            after_delete, 150,
            f"After delete expected 150, got {after_delete}",
        )


class BinFlowTests(TestCase):
    """
    Tests for move_to_bin / restore flows with inventory.
    """

    def setUp(self):
        # --- Auth client ---
        self.client = Client()
        self.user = User.objects.create_user(
            username="binuser",
            email="bin@example.com",
            password="binpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.login(username="binuser", password="binpass123")

        self.customer = Customer.objects.create(name="Bin Customer")
        self.company = CompanyProfile.objects.create(
            name="Bin Company",
            address="Indore",
        )
        self.wh = Warehouse.objects.create(name="Bin WH")

        self.prod = CatalogProduct.objects.create(
            sku="BIN-01",
            name="Bin Product",
            price=Decimal("50.00"),
            tax_rate=18,
            track_stock=True,
        )

        self.pr = PrintRun.objects.create(
            product=self.prod,
            printed_qty=100,
            received_qty=100,
            warehouse=self.wh,
        )
        StockLedger.objects.create(
            product=self.prod,
            print_run=self.pr,
            warehouse=self.wh,
            in_qty=100,
            out_qty=0,
            balance=100,
            ref_type="initial",
            ref_id=self.pr.id,
        )

        # Start stock sanity
        self.assertEqual(self.prod.available_stock(), 100)

        # Seed one invoice with 20 qty (direct create)
        inv = Invoice.objects.create(
            number="BIN-INV-1",
            customer=self.customer,
            company=self.company,
            date=timezone.localdate(),
        )
        InvoiceItem.objects.create(
            invoice=inv,
            product=self.prod,
            description=self.prod.name,
            quantity=20,
            rate=Decimal("50.00"),
            tax_rate=18,
            discount_percent=Decimal("0"),
        )

        # Allocate stock for this invoice using FIFO helper directly in test
        allocate_and_commit(
            product=self.prod,
            qty=20,
            ref_type="invoice",
            ref_id=inv.id,
            warehouse=self.wh,
            notes="Bin test allocation",
        )

        self.invoice = inv
        self.prod.refresh_from_db()
        # After allocation, stock should be 80
        self.assertEqual(self.prod.available_stock(), 80)

    def test_move_to_bin_and_restore(self):
        """
        - Move invoice to bin => stock restore to 100
        - Restore from bin    => stock goes back to 80 (re-allocation)
        """
        # 1) Move to bin
        url_bin = reverse("sales:invoice_move_to_bin", args=[self.invoice.id])
        resp = self.client.post(url_bin, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.prod.refresh_from_db()
        self.assertEqual(
            self.prod.available_stock(),
            100,
            "After moving to bin, stock should be fully restored to 100",
        )

        # 2) Restore from bin (re-allocate stock)
        url_restore = reverse("sales:invoice_restore", args=[self.invoice.id])
        resp = self.client.post(url_restore, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.prod.refresh_from_db()
        self.assertEqual(
            self.prod.available_stock(),
            80,
            "After restore, stock should again reflect 20 units consumed",
        )

