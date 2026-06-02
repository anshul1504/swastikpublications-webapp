from decimal import Decimal
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.shortcuts import render

from sales.models import Invoice, Payment, Customer
from catalog.models import Product

@login_required
@never_cache
def dashboard(request):
    today = timezone.localdate()

    # ---- CORE KPIs ----
    total_revenue = Invoice.objects.aggregate(
        total=Sum('grand_total')
    )['total'] or Decimal('0.00')

    total_paid = Payment.objects.filter(is_refund=False).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    outstanding = Invoice.objects.aggregate(
        total=Sum('balance_due')
    )['total'] or Decimal('0.00')

    unpaid_count = Invoice.objects.filter(balance_due__gt=0).count()
    paid_invoices = Invoice.objects.filter(status='paid').count()
    partial_invoices = Invoice.objects.filter(status='partial').count()

    customer_count = Customer.objects.count()
    product_count = Product.objects.count()
    total_invoices = Invoice.objects.count()

    # Average invoice value
    avg_invoice_value = Invoice.objects.aggregate(
        avg=Avg('grand_total')
    )['avg'] or Decimal('0.00')

    # Collection rate (%) = total_paid / total_revenue
    if total_revenue and total_revenue > 0:
        collection_rate = int(round((total_paid / total_revenue) * 100))
    else:
        collection_rate = 0

    # Status percentages for progress bars
    if total_invoices > 0:
        paid_pct = int(round(paid_invoices / total_invoices * 100))
        partial_pct = int(round(partial_invoices / total_invoices * 100))
        unpaid_pct = int(round(unpaid_count / total_invoices * 100))
    else:
        paid_pct = partial_pct = unpaid_pct = 0

    # ---- Overdue / today activity ----
    overdue_count = Invoice.objects.filter(
        balance_due__gt=0,
        date__lt=today
    ).count()

    today_invoices_total = Invoice.objects.filter(date=today).aggregate(
        total=Sum('grand_total')
    )['total'] or Decimal('0.00')

    today_payments_total = Payment.objects.filter(
        date=today,
        is_refund=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    today_refunds_total = Payment.objects.filter(
        date=today,
        is_refund=True
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # ---- Top customers ----
    top_customers = (
        Invoice.objects
        .values('customer__name')
        .annotate(
            total_amount=Sum('grand_total'),
            invoice_count=Count('id')
        )
        .order_by('-total_amount')[:5]
    )

    # ---- Recent invoices & payments ----
    recent_invoices = (
        Invoice.objects
        .select_related('customer')
        .order_by('-date', '-id')[:6]
    )

    recent_payments = (
        Payment.objects
        .select_related('invoice', 'invoice__customer')
        .filter(is_refund=False)
        .order_by('-date', '-id')[:6]
    )

    # ---- Revenue last 6 months ----
    labels = []
    values = []
    for i in range(5, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year = today.year + ((today.month - i - 1) // 12)
        label = f"{year}-{month:02d}"
        labels.append(label)

        m_total = (
            Invoice.objects.filter(date__year=year, date__month=month)
            .aggregate(total=Sum('grand_total'))['total']
            or Decimal('0.00')
        )
        values.append(float(m_total))

    context = {
        # KPI
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'outstanding': outstanding,
        'unpaid_count': unpaid_count,
        'paid_invoices': paid_invoices,
        'partial_invoices': partial_invoices,
        'customer_count': customer_count,
        'product_count': product_count,
        'total_invoices': total_invoices,

        # derived metrics
        'avg_invoice_value': avg_invoice_value,
        'collection_rate': collection_rate,
        'paid_pct': paid_pct,
        'partial_pct': partial_pct,
        'unpaid_pct': unpaid_pct,

        # Overdue / today
        'overdue_count': overdue_count,
        'today_invoices_total': today_invoices_total,
        'today_payments_total': today_payments_total,
        'today_refunds_total': today_refunds_total,
        'today': today,

        # Lists
        'top_customers': top_customers,
        'recent_invoices': recent_invoices,
        'recent_payments': recent_payments,

        # Chart
        'chart_labels_json': json.dumps(labels),
        'chart_values_json': json.dumps(values),
    }
    return render(request, 'dashboard.html', context)
