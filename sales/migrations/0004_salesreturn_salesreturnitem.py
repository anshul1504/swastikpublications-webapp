from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0003_invoice_bank_account_type_invoice_bank_notes_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalesReturn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("return_number", models.CharField(blank=True, max_length=30, unique=True)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("resolution", models.CharField(choices=[("refund", "Amount refund"), ("replacement", "Replacement"), ("credit", "Store credit")], max_length=20)),
                ("reason", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales_returns", to="sales.invoice")),
                ("refund_payment", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales_return", to="sales.payment")),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.CreateModel(
            name="SalesReturnItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("condition", models.CharField(choices=[("saleable", "Good / saleable"), ("damaged", "Damaged")], default="saleable", max_length=20)),
                ("invoice_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="return_items", to="sales.invoiceitem")),
                ("sales_return", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="sales.salesreturn")),
            ],
        ),
        migrations.AddConstraint(
            model_name="salesreturnitem",
            constraint=models.UniqueConstraint(fields=("sales_return", "invoice_item"), name="unique_item_per_sales_return"),
        ),
    ]
