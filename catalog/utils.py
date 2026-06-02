# catalog/utils.py
from .models_stock import StockLedger, PrintRun
from decimal import Decimal

def recompute_printrun_balances(pr_id):
    pr = PrintRun.objects.get(pk=pr_id)
    ledgers = StockLedger.objects.filter(print_run=pr).order_by('id')
    running = Decimal('0')
    for l in ledgers:
        in_q = getattr(l, 'in_qty', getattr(l, 'in', Decimal('0'))) or Decimal('0')
        out_q = getattr(l, 'out_qty', getattr(l, 'out', Decimal('0'))) or Decimal('0')
        running = running + in_q - out_q
        l.balance = running
        l.save(update_fields=['balance'])
    # optionally update cached fields
    if hasattr(pr, 'quantity'):
        pr.quantity = running
        pr.save(update_fields=['quantity'])
    elif hasattr(pr, 'available'):
        pr.available = running
        pr.save(update_fields=['available'])
    return running
