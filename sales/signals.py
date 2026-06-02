from decimal import Decimal

from django.apps import apps
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

Invoice = apps.get_model("sales", "Invoice")
Payment = apps.get_model("sales", "Payment")
InvoiceItem = apps.get_model("sales", "InvoiceItem")


@receiver(post_save, sender=InvoiceItem)
@receiver(post_delete, sender=InvoiceItem)
def invoiceitem_changed(sender, instance, **kwargs):
    inv = instance.invoice
    if inv:
        inv.recalc_totals()


@receiver(post_save, sender=Payment)
@receiver(post_delete, sender=Payment)
def payment_changed(sender, instance, **kwargs):
    inv = instance.invoice
    if not inv:
        return

    try:
        inv.recalc_payments_and_status()
    except Exception:
        paid = Decimal("0.00")
        for p in inv.payments.all():
            if not getattr(p, "is_refund", False):
                paid += Decimal(p.amount or 0)
        balance = inv.grand_total - paid
        inv.paid_amount = paid
        inv.balance_due = balance if balance > 0 else Decimal("0.00")
        inv.status = "paid" if balance <= 0 else ("partial" if paid > 0 else "unpaid")
        inv.save(update_fields=["paid_amount", "balance_due", "status"])
