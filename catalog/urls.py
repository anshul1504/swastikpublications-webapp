from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [

    # -------------------------
    # DASHBOARD / HOME
    # -------------------------
    path("inventory/", views.inventory_home, name="inventory_home"),

    # -------------------------
    # PRODUCT
    # -------------------------
    path("products/", views.ProductList.as_view(), name="product_list"),
    path("products/add/", views.ProductCreate.as_view(), name="product_add"),
    path("products/<int:pk>/edit/", views.ProductUpdate.as_view(), name="product_edit"),
    path("products/<int:pk>/", views.ProductDetail.as_view(), name="product_detail"),
    path("products/<int:pk>/delete/", views.ProductDelete.as_view(), name="product_delete"),
    path("products/<int:pk>/stock/", views.product_stock_detail, name="product_stock_detail"),
    path("products/stock/", views.product_stock_search, name="product_stock_search"),
    path("products/import/xlsx/", views.product_import_xlsx, name="product_import_xlsx"),
    path("products/export/xlsx/", views.product_export_xlsx, name="product_export_xlsx"),

    # -------------------------
    # WAREHOUSE
    # -------------------------
    path("warehouses/", views.WarehouseList.as_view(), name="warehouse_list"),
    path("warehouses/add/", views.WarehouseCreate.as_view(), name="warehouse_add"),
    path("warehouses/<int:pk>/edit/", views.WarehouseUpdate.as_view(), name="warehouse_edit"),
    path("warehouses/<int:pk>/delete/", views.WarehouseDelete.as_view(), name="warehouse_delete"),
    path("warehouses/<int:pk>/", views.WarehouseDetail.as_view(), name="warehouse_detail"),

    # warehouse import/export
    path("warehouses/import/csv/", views.warehouse_import, name="warehouse_import"),
    path("warehouses/import/xlsx/", views.warehouse_import_xlsx, name="warehouse_import_xlsx"),
    path("warehouses/export/csv/", views.warehouse_export, name="warehouse_export"),
    path("warehouses/export/xlsx/", views.warehouse_export_xlsx, name="warehouse_export_xlsx"),
    path("warehouses/<int:pk>/deactivate/", views.warehouse_deactivate, name="warehouse_deactivate"),
    path("warehouses/<int:pk>/inline-update/", views.WarehouseUpdate.as_view(),
        name="warehouse_inline_update"),


    # -------------------------
    # PRINT-RUN (BATCHES)
    # -------------------------
    path("print-runs/", views.PrintRunList.as_view(), name="pr_list"),

    # ⛔ IMPORTANT FIX — use alias, not Enterprise directly
    path("print-runs/add/", views.PrintRunCreate.as_view(), name="pr_create"),

    path("print-runs/<int:pk>/edit/", views.PrintRunUpdateEnterprise.as_view(), name="pr_edit"),
    path("print-runs/<int:pk>/delete/", views.PrintRunDeleteEnterprise.as_view(), name="pr_delete"),
    path("print-runs/<int:pk>/", views.pr_detail, name="pr_detail"),

    # export print-runs
    path("print-runs/export/csv/", views.export_csv, name="export_csv"),

    # -------------------------
    # STOCK LEDGER
    # -------------------------
    path("ledger/", views.StockLedgerList.as_view(), name="stock_ledger"),
    path("ledger/<int:pk>/edit/", views.StockLedgerUpdate.as_view(), name="stock_ledger_edit"),
    path("ledger/<int:pk>/delete/", views.stock_ledger_delete, name="stock_ledger_delete"),
    path("ledger/<int:pk>/detail/", views.stock_ledger_detail, name="stock_ledger_detail"),

    # quick edit
    path("ledger/<int:pk>/quick-edit/", views.stock_ledger_quick_edit, name="stock_ledger_quick_edit"),

    # Export ledger
    path("ledger/export/", views.stock_ledger_export, name="stock_ledger_export"),

    # -------------------------
    # API ENDPOINTS
    # -------------------------
    path("api/product-stock/", views.product_stock_api, name="product_stock_api"),
    path("api/product/<int:pk>/printruns/", views.api_product_printruns, name="api_product_printruns"),
    path("api/allocate-preview/<int:pk>/", views.api_allocate_preview, name="api_allocate_preview"),
    path("api/printrun/create/", views.api_printrun_create_v2, name="api_printrun_create_v2"),
    path("api/adjustment/create/", views.api_create_adjustment_v2, name="api_create_adjustment_v2"),

    # -------------------------
    # GENERIC TRANSACTION LINKS — SAFE
    # -------------------------
    path("transaction/<str:ref_type>/<int:ref_id>/", views.transaction_detail, name="transaction_detail"),
    path("transaction/<str:ref_type>/<int:ref_id>/edit/", views.transaction_edit, name="transaction_edit"),
    path("transaction/<str:ref_type>/<int:ref_id>/delete/", views.transaction_delete, name="transaction_delete"),

    


]
