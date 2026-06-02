# catalog/models.py
from django.db import models
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db.models import Sum
from decimal import Decimal

TAX_CHOICES = ((0, '0%'), (5, '5%'), (12, '12%'), (18, '18%'), (28, '28%'))
FORMAT_CHOICES = (
    ('PB', 'Paperback'),
    ('HB', 'Hardcover'),
    ('SB', 'Softbound'),
    ('EB', 'Ebook'),
    ('DB', 'Digital Bundle'),
)
CLASS_GRADE_CHOICES = (
    ('LKG', 'LKG'),
    ('UKG', 'UKG'),
    ('1', 'Class 1'),
    ('2', 'Class 2'),
    ('3', 'Class 3'),
    ('4', 'Class 4'),
    ('5', 'Class 5'),
    ('6', 'Class 6'),
    ('7', 'Class 7'),
    ('8', 'Class 8'),
    ('9', 'Class 9'),
    ('10', 'Class 10'),
    ('11', 'Class 11'),
    ('12', 'Class 12'),
    ('ALL', 'All Grades / General'),
)

PRODUCT_TYPE_CHOICES = (
    ('BOOK', 'Book'),
    ('SET', 'Set / Bundle'),
    ('DIGITAL', 'Digital'),
    ('OTHER', 'Other'),
)

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.PositiveIntegerField(choices=TAX_CHOICES, default=18)
    hsn_code = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r"^\d{6,8}$", message="HSN code must be 6 to 8 numeric digits.")],
    )

    is_service = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    is_bundle = models.BooleanField(default=False)
    track_stock = models.BooleanField(default=True)
    default_warehouse = models.CharField(max_length=200, blank=True, null=True)

    reorder_level = models.PositiveIntegerField(default=0)

    image = models.ImageField(upload_to='products/', blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True)
    format = models.CharField(max_length=3, choices=FORMAT_CHOICES, default='PB')
    language = models.CharField(max_length=50, blank=True, null=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    weight_grams = models.PositiveIntegerField(blank=True, null=True)
    dimensions = models.CharField(max_length=120, blank=True, null=True)
    class_grade = models.CharField(max_length=10, choices=CLASS_GRADE_CHOICES, default='ALL')
    subject = models.CharField(max_length=120, blank=True, null=True)
    author = models.CharField(max_length=160, blank=True, null=True)
    imprint = models.CharField(max_length=120, blank=True, null=True)
    edition = models.CharField(max_length=60, blank=True, null=True)
    academic_session = models.CharField(max_length=20, blank=True, null=True)

    digital_file = models.FileField(
        upload_to='digital_products/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'epub', 'mobi', 'zip'])],
        blank=True, null=True
    )
    digital_license_info = models.TextField(blank=True, null=True)

    bundle_items = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='bundled_in')
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default='BOOK')
    active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['sku', 'name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['isbn']),
            models.Index(fields=['class_grade']),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    def is_physical(self):
        return (not self.is_service) and (not self.is_digital)

    def available_stock(self):
        """
        Single source of truth: total stock = sum(StockLedger.in_qty - out_qty) for this product.
        PrintRun, received_qty wagaira sirf meta info hai.
        """
        from .models_stock import StockLedger, PrintRun  # ← dono lao
        agg = StockLedger.objects.filter(product=self).aggregate(
            total_in=models.Sum("in_qty"),
            total_out=models.Sum("out_qty"),
        )
        total_in = int(agg["total_in"] or 0)
        total_out = int(agg["total_out"] or 0)
        onhand = total_in - total_out
        return max(0, onhand)
    
    def available_stock_warehouse(self, warehouse):
        """
        Specific warehouse mein kitna stock hai is product ka.
        Ledger-based – single source of truth.
        """
        from .models_stock import StockLedger
        agg = StockLedger.objects.filter(
            product=self,
            warehouse=warehouse
        ).aggregate(
            total_in=Sum("in_qty"),
            total_out=Sum("out_qty"),
        )
        total_in = int(agg["total_in"] or 0)
        total_out = int(agg["total_out"] or 0)
        return max(0, total_in - total_out)

    def is_set(self):
        return self.product_type == 'SET' or self.is_bundle


class BookSetItem(models.Model):
    set_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='set_items')
    book_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='part_of_sets')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('set_product', 'book_product')

    def __str__(self):
        return f"{self.set_product.sku} → {self.book_product.sku} × {self.quantity}"

