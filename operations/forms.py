from decimal import Decimal

from django import forms
from django.db.models import Q
from django.utils import timezone

from fleet.models import *

from .models import*


class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):
                field.widget.attrs["class"] = (
                    "form-check-input"
                )

            else:
                field.widget.attrs["class"] = (
                    "form-control"
                )


class TripForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = Trip

        fields = [
            "source",
            "destination",
            "vehicle",
            "driver",
            "cargo_weight",
            "planned_distance",
            "revenue",
            "notes",
        ]

        widgets = {
            "cargo_weight": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01",
                }
            ),

            "planned_distance": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01",
                }
            ),

            "revenue": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        available_vehicles = Vehicle.objects.filter(
            status=Vehicle.Status.AVAILABLE
        )

        valid_drivers = Driver.objects.filter(
            status=Driver.Status.AVAILABLE,
            license_expiry_date__gte=timezone.localdate(),
        )

        if self.instance and self.instance.pk:
            available_vehicles = Vehicle.objects.filter(
                Q(status=Vehicle.Status.AVAILABLE)
                | Q(pk=self.instance.vehicle_id)
            )

            valid_drivers = Driver.objects.filter(
                Q(
                    status=Driver.Status.AVAILABLE,
                    license_expiry_date__gte=timezone.localdate(),
                )
                | Q(pk=self.instance.driver_id)
            )

        self.fields["vehicle"].queryset = (
            available_vehicles
        )

        self.fields["driver"].queryset = valid_drivers

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        source = cleaned_data.get("source")
        destination = cleaned_data.get("destination")
        vehicle = cleaned_data.get("vehicle")
        driver = cleaned_data.get("driver")
        cargo_weight = cleaned_data.get("cargo_weight")

        if (
            source
            and destination
            and source.strip().lower()
            == destination.strip().lower()
        ):
            self.add_error(
                "destination",
                "Source and destination cannot be the same.",
            )

        if (
            vehicle
            and cargo_weight
            and cargo_weight
            > vehicle.maximum_load_capacity
        ):
            self.add_error(
                "cargo_weight",
                (
                    f"Maximum capacity is "
                    f"{vehicle.maximum_load_capacity} kg."
                ),
            )

        if (
            vehicle
            and vehicle.status
            != Vehicle.Status.AVAILABLE
        ):
            self.add_error(
                "vehicle",
                "This vehicle is not available.",
            )

        if driver:
            if driver.status != Driver.Status.AVAILABLE:
                self.add_error(
                    "driver",
                    "This driver is not available.",
                )

            elif driver.is_license_expired:
                self.add_error(
                    "driver",
                    "This driver's licence has expired.",
                )

        return cleaned_data


class TripCompleteForm(
    BootstrapFormMixin,
    forms.Form,
):
    final_odometer = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
    )

    fuel_consumed = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        help_text="Fuel consumed in litres.",
    )

    def __init__(self, *args, trip=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.trip = trip

        self.fields["final_odometer"].widget.attrs.update(
            {
                "step": "0.01",
                "min": (
                    str(trip.start_odometer)
                    if trip and trip.start_odometer is not None
                    else "0"
                ),
            }
        )

        self.fields["fuel_consumed"].widget.attrs.update(
            {
                "step": "0.01",
                "min": "0.01",
            }
        )

        self.apply_bootstrap()

    def clean_final_odometer(self):
        final_odometer = self.cleaned_data[
            "final_odometer"
        ]

        if (
            self.trip
            and self.trip.start_odometer is not None
            and final_odometer
            < self.trip.start_odometer
        ):
            raise forms.ValidationError(
                (
                    f"Final odometer must be at least "
                    f"{self.trip.start_odometer} km."
                )
            )

        return final_odometer
    
class MaintenanceCreateForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = MaintenanceRecord

        fields = [
            "vehicle",
            "maintenance_type",
            "description",
            "priority",
            "estimated_cost",
            "expected_completion_date",
        ]

        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 4}
            ),
            "estimated_cost": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "expected_completion_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vehicle"].queryset = Vehicle.objects.filter(
            status=Vehicle.Status.AVAILABLE
        )

        self.apply_bootstrap()

    def clean_expected_completion_date(self):
        value = self.cleaned_data.get(
            "expected_completion_date"
        )

        if value and value < timezone.localdate():
            raise forms.ValidationError(
                "Expected completion date cannot be in the past."
            )

        return value


class MaintenanceCloseForm(
    BootstrapFormMixin,
    forms.Form,
):
    final_cost = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
    )

    completion_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class FuelLogForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = FuelLog

        fields = [
            "vehicle",
            "trip",
            "date",
            "liters",
            "price_per_liter",
            "odometer",
            "notes",
        ]

        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "liters": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "price_per_liter": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "odometer": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        vehicle = cleaned_data.get("vehicle")
        trip = cleaned_data.get("trip")
        odometer = cleaned_data.get("odometer")

        if trip and vehicle and trip.vehicle_id != vehicle.id:
            self.add_error(
                "trip",
                "This trip does not belong to the selected vehicle.",
            )

        if (
            vehicle
            and odometer is not None
            and odometer < vehicle.odometer
        ):
            self.add_error(
                "odometer",
                (
                    f"Odometer cannot be below the current "
                    f"vehicle odometer of {vehicle.odometer} km."
                ),
            )

        return cleaned_data


class ExpenseForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = Expense

        fields = [
            "vehicle",
            "trip",
            "expense_type",
            "description",
            "amount",
            "date",
        ]

        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        vehicle = cleaned_data.get("vehicle")
        trip = cleaned_data.get("trip")

        if trip and vehicle and trip.vehicle_id != vehicle.id:
            self.add_error(
                "trip",
                "This trip does not belong to the selected vehicle.",
            )

        return cleaned_data