from django import forms
from django.utils import timezone

from .models import Driver, Vehicle


class BootstrapModelForm(forms.ModelForm):
    """Apply Bootstrap classes to all fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class VehicleForm(BootstrapModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "registration_number",
            "vehicle_name",
            "model",
            "vehicle_type",
            "maximum_load_capacity",
            "odometer",
            "acquisition_cost",
            "region",
            "status",
        ]

        widgets = {
            "maximum_load_capacity": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "odometer": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "acquisition_cost": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }

    def clean_registration_number(self):
        registration_number = (
            self.cleaned_data["registration_number"]
            .upper()
            .strip()
        )

        duplicate = Vehicle.objects.filter(
            registration_number=registration_number
        )

        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise forms.ValidationError(
                "A vehicle with this registration number already exists."
            )

        return registration_number


class DriverForm(BootstrapModelForm):
    class Meta:
        model = Driver
        fields = [
            "name",
            "license_number",
            "license_category",
            "license_expiry_date",
            "contact_number",
            "safety_score",
            "status",
        ]

        widgets = {
            "license_expiry_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "safety_score": forms.NumberInput(
                attrs={
                    "min": "0",
                    "max": "100",
                }
            ),
        }

    def clean_license_number(self):
        license_number = (
            self.cleaned_data["license_number"]
            .upper()
            .strip()
        )

        duplicate = Driver.objects.filter(
            license_number=license_number
        )

        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise forms.ValidationError(
                "A driver with this licence number already exists."
            )

        return license_number

    def clean(self):
        cleaned_data = super().clean()

        expiry_date = cleaned_data.get("license_expiry_date")
        status = cleaned_data.get("status")

        if (
            expiry_date
            and expiry_date < timezone.localdate()
            and status == Driver.Status.AVAILABLE
        ):
            self.add_error(
                "status",
                "A driver with an expired licence cannot be Available.",
            )

        return cleaned_data