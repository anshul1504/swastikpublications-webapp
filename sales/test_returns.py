from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Product
from catalog.models_stock import PrintRun, StockLedger, Warehouse
from sales.models import Customer, Invoice, InvoiceItem, Payment, SalesReturn


class SalesReturnWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="returns", password="pass")
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(name="Return Customer")
        self.warehouse = Warehouse.objects.create(name="Returns WH")
        self.product = Product.objects.create(
            sku="BOOK-RET", name="Returnable Book", price=Decimal("100"), track_stock=True
        )
        self.print_run = PrintRun.objects.create(
            product=self.product, printed_qty=20, received_qty=20, warehouse=self.warehouse
        )
        self.invoice = Invoice.objects.create(
            number="INV-RETURN-1", date=timezone.localdate(), customer=self.customer,
            grand_total=Decimal("500"), paid_amount=Decimal("500"),
        )
        self.item = InvoiceItem.objects.create(
            invoice=self.invoice, product=self.product, description="Returnable Book",
            quantity=5, rate=Decimal("100"),
        )
        StockLedger.objects.create(
            product=self.product, print_run=self.print_run, warehouse=self.warehouse,
            in_qty=20, out_qty=0, balance=20, ref_type="initial", ref_id=self.print_run.id,
        )
        StockLedger.objects.create(
            product=self.product, print_run=self.print_run, warehouse=self.warehouse,
            in_qty=0, out_qty=5, balance=15, ref_type="invoice", ref_id=self.invoice.id,
        )
        Payment.objects.create(invoice=self.invoice, amount=Decimal("500"), method="Cash")

    def test_damaged_replacement_does_not_restock_damaged_copy(self):
        response = self.client.post(reverse("sales:return_add"), {
            "invoice": self.invoice.id,
            "resolution": "replacement",
            "date": timezone.localdate().isoformat(),
            "reason": "Damaged in transit",
            "item_id[]": [self.item.id],
            "quantity[]": [2],
            "condition[]": ["damaged"],
        })
        self.assertEqual(response.status_code, 302)
        sales_return = SalesReturn.objects.get()
        self.assertEqual(sales_return.total_quantity, 2)
        self.assertFalse(
            StockLedger.objects.filter(ref_type="sales_return", ref_id=sales_return.id).exists()
        )
        replacement = StockLedger.objects.filter(
            ref_type="sales_return_replacement", ref_id=sales_return.id
        )
        self.assertEqual(sum(row.out_qty for row in replacement), 2)

    def test_good_return_with_refund_restock_and_records_refund(self):
        response = self.client.post(reverse("sales:return_add"), {
            "invoice": self.invoice.id,
            "resolution": "refund",
            "refund_method": "UPI",
            "date": timezone.localdate().isoformat(),
            "reason": "Wrong book supplied",
            "item_id[]": [self.item.id],
            "quantity[]": [1],
            "condition[]": ["saleable"],
        })
        self.assertEqual(response.status_code, 302)
        sales_return = SalesReturn.objects.get()
        self.assertEqual(sales_return.refund_payment.amount, Decimal("100.00"))
        self.assertTrue(sales_return.refund_payment.is_refund)
        restock = StockLedger.objects.get(ref_type="sales_return", ref_id=sales_return.id)
        self.assertEqual(restock.in_qty, 1)
