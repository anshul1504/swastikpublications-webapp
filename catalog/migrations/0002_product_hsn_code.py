from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="hsn_code",
            field=models.CharField(
                blank=True,
                max_length=8,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="HSN code must be 6 to 8 numeric digits.", regex="^\\d{6,8}$"
                    )
                ],
            ),
        ),
    ]
