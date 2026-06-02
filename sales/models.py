from django.db import models
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from catalog.models import Product


class Customer(models.Model):
    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    customer_type = models.CharField(max_length=50, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    pan = models.CharField(max_length=15, blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # ✅ Add these two fields
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def update_balance_from_invoices(self):
        """Auto calculate total spent and pending balance"""
        total = self.invoices.aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')
        paid = self.invoices.aggregate(paid=Sum('paid_amount'))['paid'] or Decimal('0.00')

        self.total_spent = total.quantize(Decimal('0.01'))
        self.pending_balance = (total - paid).quantize(Decimal('0.01'))
        self.save(update_fields=['total_spent', 'pending_balance'])




class SavedItem(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.PositiveIntegerField(default=18)
    is_service = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# sales/models.py (relevant parts)

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ]

    number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    company = models.ForeignKey(
        'CompanyProfile',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invoices'
    )
    customer = models.ForeignKey(
        'Customer',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invoices'
    )

    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    terms = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # totals stored for convenience
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # payments/status
    # 🟢 IMPORTANT: yahan hum NET RECEIVED store karenge (payments - refunds)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    manual_status = models.BooleanField(default=False)

    bank_name = models.CharField(max_length=200, blank=True)
    bank_branch = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    ifsc = models.CharField(max_length=50, blank=True)
    upi = models.CharField(max_length=100, blank=True)
    bank_account_type = models.CharField(max_length=50, blank=True)
    bank_notes = models.TextField(blank=True)
    signatory_name = models.CharField(max_length=160, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    in_bin = models.BooleanField(default=False)  # soft delete / move to bin
    deleted_at = models.DateTimeField(null=True, blank=True)  # kab bin me gaya


    # ---------- TOTALS FROM ITEMS ----------
    def recalc_totals(self):
        """Recompute subtotal, tax, discounts, grand_total from related items"""
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')
        discount_total = Decimal('0.00')

        for it in self.items.all():
            qty = Decimal(it.quantity or 0)
            rate = Decimal(it.rate or 0)
            tax = Decimal(it.tax_rate or 0)
            disc_pct = Decimal(it.discount_percent or 0)

            line = qty * rate
            disc_amt = (line * disc_pct) / Decimal('100.00')
            taxed = (line - disc_amt) * (tax / Decimal('100.00'))

            subtotal += line
            discount_total += disc_amt
            tax_total += taxed

            it.line_total = (line - disc_amt) + taxed
            it.save(update_fields=['line_total'])

        grand_total = subtotal - discount_total + tax_total

        self.subtotal = subtotal.quantize(Decimal('0.01'))
        self.discount_total = discount_total.quantize(Decimal('0.01'))
        self.tax_total = tax_total.quantize(Decimal('0.01'))
        self.grand_total = grand_total.quantize(Decimal('0.01'))
        self.save(update_fields=['subtotal', 'discount_total', 'tax_total', 'grand_total'])

    # ---------- PAYMENTS + REFUNDS ----------
    def recalc_payments_and_status(self):
        """
        Recompute NET paid_amount (payments - refunds),
        balance_due and status using Payment.is_refund flag.
        """
        # Total payments (money received)
        paid_total = self.payments.filter(is_refund=False).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Total refunds (money returned)
        refunded_total = self.payments.filter(is_refund=True).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        net_received = paid_total - refunded_total
        if net_received < 0:
            net_received = Decimal('0.00')

        balance = self.grand_total - net_received
        if balance <= 0:
            computed_status = 'paid'
            balance = Decimal('0.00')
        elif net_received > 0:
            computed_status = 'partial'
        else:
            computed_status = 'unpaid'

        self.paid_amount = net_received.quantize(Decimal('0.01'))
        self.balance_due = balance.quantize(Decimal('0.01'))
        if not self.manual_status:
            self.status = computed_status
        self.save(update_fields=['paid_amount', 'balance_due', 'status'])

    def save(self, *args, **kwargs):
        """
        Override save to auto-update related customer balances.
        (Whenever invoice totals/status change, customer ka balance bhi update ho)
        """
        super().save(*args, **kwargs)
        if self.customer:
            self.customer.update_balance_from_invoices()

    def delete(self, *args, **kwargs):
        """Update customer balance if invoice deleted"""
        customer = self.customer
        super().delete(*args, **kwargs)
        if customer:
            customer.update_balance_from_invoices()

    def __str__(self):
        return self.number

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    saved_item = models.ForeignKey('SavedItem', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    hsn_code = models.CharField(max_length=8, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.PositiveIntegerField(default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def recalc(self):
        line = self.quantity * self.rate
        disc_amt = line * (Decimal(self.discount_percent) / Decimal('100'))
        taxable = (line - disc_amt)
        tax_amt = taxable * (Decimal(self.tax_rate) / Decimal('100'))
        total = (taxable + tax_amt)
        self.line_total = total.quantize(Decimal('0.01'))
        return self.line_total

    def save(self, *args, **kwargs):
        self.recalc()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description or 'Item'} ({self.invoice.number})"

class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    method = models.CharField(max_length=50, default='Cash')
    note = models.CharField(max_length=255, blank=True)

    # 🟢 IMPORTANT FIELD: ye batata hai payment hai ya refund
    is_refund = models.BooleanField(default=False)

    def __str__(self):
        kind = "Refund" if self.is_refund else "Payment"
        return f"{kind} {self.invoice.number} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        """
        Payment / Refund create or update hone par
        invoice ke totals & status auto recalc ho jaye.
        """
        super().save(*args, **kwargs)
        if self.invoice_id:
            try:
                self.invoice.recalc_payments_and_status()
            except Exception:
                pass

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        if invoice:
            try:
                invoice.recalc_payments_and_status()
            except Exception:
                pass


class CompanyProfile(models.Model):
    name = models.CharField(max_length=255, default="The Webfix")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField(max_length=20, blank=True)
    bank_details = models.TextField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)

    def __str__(self):
        return self.name

# 🔵 Legacy Refund model (agar pehle se data hai to use rakho)
class Refund(models.Model):
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE, related_name='refunds', null=True, blank=True)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    date = models.DateField(default=timezone.localdate)
    method = models.CharField(max_length=50, default='Refund')
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund {self.pk} — ₹{self.amount}"
