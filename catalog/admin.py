# catalog/admin.py
from django.contrib import admin
from .models import Product, BookSetItem
from . import models_stock

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "product_type", "class_grade", "subject", "price", "track_stock", "active")
    search_fields = ("sku", "name", "isbn", "subject")
    list_filter = ("product_type", "class_grade", "track_stock", "active")
    list_editable = ("price", "track_stock", "active")
    readonly_fields = ("created_at", "updated_at")

class BookSetItemInline(admin.TabularInline):
    model = BookSetItem
    extra = 1
    autocomplete_fields = ('book_product',)

@admin.register(BookSetItem)
class BookSetItemAdmin(admin.ModelAdmin):
    list_display = ("set_product", "book_product", "quantity")
    search_fields = ("set_product__sku", "book_product__sku")

# Register stock models
@admin.register(models_stock.Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name','phone','email')
    search_fields = ('name',)

@admin.register(models_stock.PrintRun)
class PrintRunAdmin(admin.ModelAdmin):
    list_display = ('product','batch_no','received_qty','printed_qty','unit_cost','print_date','warehouse')
    search_fields = ('batch_no','product__sku','product__name')
    list_filter = ('warehouse','print_date')
    readonly_fields = ('available_admin_readonly',)

    def available_admin_readonly(self, obj):
        try:
            return obj.available_qty()
        except Exception:
            return None
    available_admin_readonly.short_description = "Available (computed)"

@admin.register(models_stock.StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ('product','print_run','warehouse','in_qty','out_qty','balance','ref_type','ref_id','date')
    search_fields = ('product__sku','ref_type')
    list_filter = ('ref_type','warehouse')
