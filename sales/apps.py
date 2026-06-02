from django.apps import AppConfig

class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'

    def ready(self):
        # Temporarily disable automatic signal import while debugging DB lock/hang.
        # Comment out signals import to test whether signals are causing long-running DB ops.
        # import sales.signals  # <-- comment out for now (uncomment after debugging)
        return
