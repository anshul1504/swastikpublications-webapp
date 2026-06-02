from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from .models import Product
from .models_stock import PrintRun, StockLedger


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = apps.get_model("catalog", "Warehouse")
        fields = [
            "name",
            "code",
            "manager_name",
            "address",
            "phone",
            "email",
            "opening_hours",
            "notes",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "manager_name": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "opening_hours": forms.HiddenInput(),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            return name
        qs = self.Meta.model.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A warehouse with this name already exists.")
        return name


class PrintRunForm(forms.ModelForm):
    class Meta:
        model = PrintRun
        fields = [
            "product",
            "batch_no",
            "printed_qty",
            "received_qty",
            "unit_cost",
            "print_date",
            "warehouse",
            "notes",
        ]


class StockLedgerForm(forms.ModelForm):
    class Meta:
        model = StockLedger
        fields = ["product", "print_run", "warehouse", "in_qty", "out_qty", "notes"]


class StockLedgerEditForm(forms.ModelForm):
    adjust_qty = forms.IntegerField(required=False)

    class Meta:
        model = StockLedger
        fields = ["notes"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "hsn_code",
            "author",
            "imprint",
            "edition",
            "academic_session",
            "description",
            "price",
            "mrp",
            "tax_rate",
            "track_stock",
            "reorder_level",
            "image",
            "active",
        ]
        widgets = {
            "hsn_code": forms.TextInput(
                attrs={"class": "form-input", "maxlength": 8, "placeholder": "e.g. 490110"}
            ),
            "author": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. NCERT Editorial Team"}),
            "imprint": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Swastik Publications"}),
            "edition": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 3rd Edition"}),
            "academic_session": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 2026-27"}),
        }

    def clean_hsn_code(self):
        hsn = (self.cleaned_data.get("hsn_code") or "").strip()
        if not hsn:
            return ""
        if not hsn.isdigit() or len(hsn) not in (6, 7, 8):
            raise ValidationError("HSN code must be 6 to 8 numeric digits.")
        return hsn
