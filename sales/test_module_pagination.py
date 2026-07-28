from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from sales.models import Customer, Invoice, Payment, SalesReturn


class ModulePaginationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="module-pages", password="pass"
        )
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(name="Module Customer")
        self.invoice = Invoice.objects.create(
            number="MODULE-INV-1",
            date=timezone.localdate(),
            customer=self.customer,
            grand_total=Decimal("100.00"),
            balance_due=Decimal("100.00"),
        )
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("25.00"),
            method="Cash",
            is_refund=False,
        )
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("5.00"),
            method="Cash",
            is_refund=True,
        )
        SalesReturn.objects.create(
            invoice=self.invoice,
            resolution="credit",
            reason="Customer return",
        )
        Invoice.objects.create(
            number="MODULE-BIN-1",
            date=timezone.localdate(),
            customer=self.customer,
            in_bin=True,
        )

    def test_all_growing_sales_lists_use_safe_pagination(self):
        urls = [
            reverse("sales:customer_list"),
            reverse("sales:payment_list"),
            reverse("sales:refund_list"),
            reverse("sales:invoice_bin_list"),
            reverse("sales:return_list"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(
                    url, {"page": "not-a-number", "page_size": "999"}
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("page_obj", response.context)
                self.assertEqual(response.context["page_size"], 25)
                self.assertContains(response, "Rows")
