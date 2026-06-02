from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path('', views.invoice_list, name='invoice_list'),
    path('invoices/add/', views.invoice_add, name='invoice_add'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_add, name='customer_add'),
    path('customers/add/ajax/', views.customer_add_ajax, name='customer_add_ajax'),    
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('saved-items/add-ajax/', views.save_item_ajax, name='save_item_ajax'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/export/', views.payment_export_csv, name='payment_export_csv'),
    path('payments/add/', views.payment_add, name='payment_add'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('reports/payments-dashboard/', views.payments_dashboard, name='payments_dashboard'),
    # unpaid invoices / collection center
    path('invoices/unpaid/', views.unpaid_invoices, name='unpaid_invoices'),
    path("unpaid/", views.unpaid_invoices, name="unpaid_invoices"),
    path("unpaid/bulk_mark_paid/", views.bulk_mark_paid, name="bulk_mark_paid"),
    path('invoices/<int:pk>/mark-paid/', views.invoice_mark_paid, name='invoice_mark_paid'),
    # refunds
    path('refunds/add/', views.refund_add, name='refund_add'),
    path("refunds/", views.refund_list, name="refund_list"),
    path('refunds/<int:pk>/', views.refund_detail, name='refund_detail'),
    path('refunds/<int:pk>/delete/', views.refund_delete, name='refund_delete'),   
    path('inventory/', views.inventory_home, name='inventory_home'),    
    path('invoices/<int:pk>/preview/', views.invoice_preview, name='invoice_preview'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('customers/<int:pk>/details/', views.customer_details_ajax, name='customer_details_ajax'),
    path('customer/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customer/<int:pk>/statement/', views.customer_statement_pdf, name='customer_statement_pdf'),
    path('invoice/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoice/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoice/<int:pk>/bin/', views.invoice_move_to_bin, name='invoice_move_to_bin'),
    path('invoices/bin/', views.invoice_bin_list, name='invoice_bin_list'),
    path('invoice/<int:pk>/restore/', views.invoice_restore, name='invoice_restore'),
    path('invoice/<int:pk>/bin-delete/', views.invoice_bin_delete, name='invoice_bin_delete'),    
    path("payments/statement/pdf/", views.payments_statement_pdf, name="payments_statement_pdf"),
    path("refunds/<int:pk>/pdf/", views.refund_pdf, name="refund_pdf"),
    path("refunds/<int:pk>/edit/", views.refund_edit, name="refund_edit"),
    path("refunds/statement/", views.refund_statement_pdf, name="refund_statement_pdf"),
    path('api/company/<int:pk>/', views.company_info_api, name='api_company_info'),
    path('invoices/bulk-action/', views.bulk_invoice_action, name='bulk_invoice_action'),
    path('api/invoice-items/<int:invoice_id>/', views.invoice_items_api, name='api_invoice_items')
]
