from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from sales.models import Customer, Invoice, Payment


class InvoiceListExperienceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="invoice-list-user", password="pass"
        )
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(
            name="Pagination Customer", email="pages@example.com"
        )

    def test_invoice_list_is_paginated_and_filtered(self):
        today = timezone.localdate()
        for index in range(31):
            Invoice.objects.create(
                number=f"PAGE-{index:03d}",
                date=today - timedelta(days=index),
                customer=self.customer,
                grand_total=Decimal("100.00"),
                balance_due=Decimal("100.00"),
            )

        response = self.client.get(
            reverse("sales:invoice_list"),
            {"q": "PAGE", "page_size": "25", "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 31)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["invoices"]), 6)
        self.assertContains(response, "Showing <strong>26-31</strong>")

    def test_bulk_mark_paid_does_not_double_count_payment(self):
        invoice = Invoice.objects.create(
            number="BULK-PAID-1",
            date=timezone.localdate(),
            customer=self.customer,
            grand_total=Decimal("100.00"),
            balance_due=Decimal("100.00"),
        )

        response = self.client.post(
            reverse("sales:bulk_invoice_action"),
            {"invoice_ids[]": [invoice.id], "action": "mark_paid"},
        )

        self.assertEqual(response.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal("100.00"))
        self.assertEqual(invoice.balance_due, Decimal("0.00"))
        self.assertEqual(
            Payment.objects.filter(invoice=invoice, is_refund=False).count(), 1
        )
