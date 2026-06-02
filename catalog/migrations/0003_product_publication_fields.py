from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_product_hsn_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="author",
            field=models.CharField(blank=True, max_length=160, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="imprint",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="edition",
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="academic_session",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
