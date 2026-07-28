from django import forms

from .models import CompanyProfile


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = (
            "name", "legal_name", "logo", "address", "phone", "email", "website",
            "gstin", "pan", "state_code", "bank_details", "invoice_prefix",
            "invoice_terms", "is_active", "is_default",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "bank_details": forms.Textarea(attrs={"rows": 4}),
            "invoice_terms": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
            field.widget.attrs["class"] = css
        self.fields["name"].widget.attrs["placeholder"] = "Display name"
        self.fields["gstin"].widget.attrs["placeholder"] = "e.g. 09ABCDE1234F1Z5"
        self.fields["invoice_prefix"].widget.attrs["placeholder"] = "e.g. SP"

    def clean_gstin(self):
        return (self.cleaned_data.get("gstin") or "").strip().upper()

    def clean_pan(self):
        return (self.cleaned_data.get("pan") or "").strip().upper()

    def clean_state_code(self):
        value = (self.cleaned_data.get("state_code") or "").strip()
        if value and (not value.isdigit() or len(value) != 2):
            raise forms.ValidationError("State code must contain exactly 2 digits.")
        return value

    def clean_invoice_prefix(self):
        return (self.cleaned_data.get("invoice_prefix") or "").strip().upper()
