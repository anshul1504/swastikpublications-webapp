from django.contrib import admin
from .models import Customer, Invoice, InvoiceItem, Payment, SavedItem, CompanyProfile

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "date", "grand_total", "status")
    search_fields = ("number", "customer__name")
    list_filter = ("status", "date")
    inlines = [InvoiceItemInline]

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "gstin")
    search_fields = ("name", "email", "phone")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "date")
    list_filter = ("method", "date")

@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "tax_rate", "is_service")
    list_filter = ("is_service",)

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "gstin")
