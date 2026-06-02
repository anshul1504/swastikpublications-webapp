from decimal import Decimal
from django.db.models import Sum
import pdfkit


WKHTMLTOPDF_PATH = "/home2/swaspub/bin/wkhtmltopdf"


def pdf_config():
    return pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)


def pdf_options():
    return {
        "encoding": "UTF-8",
        "enable-local-file-access": None,
    }

def compute_invoice_totals(invoice):
    subtotal = Decimal('0')
    tax_total = Decimal('0')
    discount_total = Decimal('0')
    for it in invoice.items.all():
        line = Decimal(it.quantity) * Decimal(it.rate)
        disc_amt = line * (Decimal(it.discount_percent) / Decimal('100'))
        taxable = line - disc_amt
        tax_amt = taxable * (Decimal(it.tax_rate) / Decimal('100'))
        line_total = (taxable + tax_amt).quantize(Decimal('0.01'))
        it.line_total = line_total
        it.save(update_fields=['line_total'])
        subtotal += line
        tax_total += tax_amt
        discount_total += disc_amt

    paid = invoice.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    invoice.subtotal = subtotal.quantize(Decimal('0.01'))
    invoice.tax_total = tax_total.quantize(Decimal('0.01'))
    invoice.discount_total = discount_total.quantize(Decimal('0.01'))
    invoice.grand_total = (subtotal - discount_total + tax_total).quantize(Decimal('0.01'))
    if paid >= invoice.grand_total and invoice.grand_total > 0:
        invoice.status = 'paid'
    elif paid > 0:
        invoice.status = 'partial'
    else:
        # Draft remains draft; else set unpaid
        if invoice.status == 'draft':
            invoice.status = 'unpaid'
    invoice.save(update_fields=['subtotal','tax_total','discount_total','grand_total','status'])


def aggregate_payment_totals(payments_qs):
    total_paid = payments_qs.filter(is_refund=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_refunded = payments_qs.filter(is_refund=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    net_received = total_paid - total_refunded
    return (
        total_paid.quantize(Decimal("0.01")),
        total_refunded.quantize(Decimal("0.01")),
        net_received.quantize(Decimal("0.01")),
    )


def aggregate_legacy_refunds(refunds_qs):
    total = refunds_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return total.quantize(Decimal("0.01"))


def aggregate_refunds_unified(payment_refunds_qs=None, legacy_refunds_qs=None):
    """
    Canonical refund policy for backward compatibility:
    total_refunded = Payment(is_refund=True) + legacy Refund rows.
    """
    payment_total = Decimal("0.00")
    legacy_total = Decimal("0.00")
    if payment_refunds_qs is not None:
        payment_total = payment_refunds_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    if legacy_refunds_qs is not None:
        legacy_total = legacy_refunds_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return (payment_total + legacy_total).quantize(Decimal("0.01"))
