from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from reports import views as report_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('catalog/', include(('catalog.urls', 'catalog'), namespace='catalog')),

    # ✅ ROOT = Dashboard
    path('', report_views.dashboard, name='dashboard'),

    # ✅ Sales app ab /sales/ se chalega (invoices, etc.)
    path('sales/', include(('sales.urls', 'sales'), namespace='sales')),

    # Baaki reports urls (agar alag se use karne ho)
    path('reports/', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
