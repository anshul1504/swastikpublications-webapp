from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .forms import ProductForm
from .models import Product


class ProductHSNValidationTests(TestCase):
    def test_accepts_valid_hsn_lengths(self):
        for hsn in ("123456", "1234567", "12345678"):
            form = ProductForm(
                data={
                    "sku": f"SKU-{hsn}",
                    "name": f"Book {hsn}",
                    "hsn_code": hsn,
                    "description": "",
                    "price": "100",
                    "mrp": "120",
                    "tax_rate": "18",
                    "track_stock": "on",
                    "reorder_level": "1",
                    "active": "on",
                }
            )
            self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_invalid_hsn(self):
        for hsn in ("12345", "123456789", "12AB56", ""):
            data = {
                "sku": f"SKU-X-{hsn or 'blank'}",
                "name": "Book",
                "hsn_code": hsn,
                "description": "",
                "price": "100",
                "mrp": "120",
                "tax_rate": "18",
                "track_stock": "on",
                "reorder_level": "1",
                "active": "on",
            }
            form = ProductForm(data=data)
            if hsn == "":
                self.assertTrue(form.is_valid(), form.errors)
            else:
                self.assertFalse(form.is_valid())


class ProductModelBasicsTests(TestCase):
    def test_available_stock_non_negative_without_ledger(self):
        p = Product.objects.create(
            sku="BOOK-001",
            name="Sample Book",
            price=Decimal("99.00"),
            mrp=Decimal("120.00"),
            tax_rate=18,
        )
        self.assertEqual(p.available_stock(), 0)


class ProductPublicationFieldsTests(TestCase):
    def test_product_form_accepts_publication_fields(self):
        form = ProductForm(
            data={
                "sku": "BOOK-PUB-001",
                "name": "Physics Class 10",
                "hsn_code": "490110",
                "author": "A. Sharma",
                "imprint": "Swastik Publications",
                "edition": "3rd Edition",
                "academic_session": "2026-27",
                "description": "Textbook",
                "price": "220",
                "mrp": "250",
                "tax_rate": "5",
                "track_stock": "on",
                "reorder_level": "5",
                "active": "on",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(obj.author, "A. Sharma")
        self.assertEqual(obj.imprint, "Swastik Publications")
        self.assertEqual(obj.edition, "3rd Edition")
        self.assertEqual(obj.academic_session, "2026-27")
