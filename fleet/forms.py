from django import forms

from .models import Vehicle


class VehicleForm(forms.ModelForm):
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
            "registration_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: GJ05CD4821",
                }
            ),

            "vehicle_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Tata Ace Cargo",
                }
            ),

            "model": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2024",
                }
            ),

            "vehicle_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "maximum_load_capacity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Example: 500",
                }
            ),

            "odometer": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Current odometer",
                }
            ),

            "acquisition_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Vehicle acquisition cost",
                }
            ),

            "region": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Surat",
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.original_status = None
        self.original_odometer = None

        if self.instance and self.instance.pk:
            original_vehicle = Vehicle.objects.get(
                pk=self.instance.pk
            )

            self.original_status = original_vehicle.status
            self.original_odometer = original_vehicle.odometer

            # On Trip and In Shop statuses are controlled
            # automatically by trip and maintenance workflows.
            if original_vehicle.status in [
                Vehicle.Status.ON_TRIP,
                Vehicle.Status.IN_SHOP,
            ]:
                self.fields["status"].disabled = True

                self.fields["status"].help_text = (
                    "Status cannot be changed manually while "
                    "the vehicle is On Trip or In Shop."
                )

            elif original_vehicle.status == Vehicle.Status.RETIRED:
                self.fields["status"].disabled = True

                self.fields["status"].help_text = (
                    "A retired vehicle cannot be restored manually."
                )

            else:
                # Available vehicles may remain Available or be Retired.
                self.fields["status"].choices = [
                    (
                        Vehicle.Status.AVAILABLE,
                        "Available",
                    ),
                    (
                        Vehicle.Status.RETIRED,
                        "Retired",
                    ),
                ]

        else:
            # New vehicles should not start as On Trip or In Shop.
            self.fields["status"].choices = [
                (
                    Vehicle.Status.AVAILABLE,
                    "Available",
                ),
                (
                    Vehicle.Status.RETIRED,
                    "Retired",
                ),
            ]

            self.fields["status"].initial = (
                Vehicle.Status.AVAILABLE
            )

    def clean_registration_number(self):
        registration_number = (
            self.cleaned_data["registration_number"]
            .upper()
            .strip()
        )

        duplicate_vehicle = Vehicle.objects.filter(
            registration_number__iexact=registration_number
        )

        if self.instance and self.instance.pk:
            duplicate_vehicle = duplicate_vehicle.exclude(
                pk=self.instance.pk
            )

        if duplicate_vehicle.exists():
            raise forms.ValidationError(
                "A vehicle with this registration number already exists."
            )

        return registration_number

    def clean_odometer(self):
        odometer = self.cleaned_data["odometer"]

        if (
            self.original_odometer is not None
            and odometer < self.original_odometer
        ):
            raise forms.ValidationError(
                (
                    "Odometer cannot be reduced. "
                    f"Current odometer is "
                    f"{self.original_odometer} km."
                )
            )

        return odometer

    def clean_status(self):
        status = self.cleaned_data.get("status")

        if not self.instance.pk:
            if status not in [
                Vehicle.Status.AVAILABLE,
                Vehicle.Status.RETIRED,
            ]:
                raise forms.ValidationError(
                    (
                        "A new vehicle can only be "
                        "Available or Retired."
                    )
                )

            return status

        if self.original_status in [
            Vehicle.Status.ON_TRIP,
            Vehicle.Status.IN_SHOP,
            Vehicle.Status.RETIRED,
        ]:
            return self.original_status

        if status in [
            Vehicle.Status.ON_TRIP,
            Vehicle.Status.IN_SHOP,
        ]:
            raise forms.ValidationError(
                (
                    "On Trip and In Shop statuses are changed "
                    "automatically by trip and maintenance workflows."
                )
            )

        return status
    def clean_maximum_load_capacity(self):
        capacity = self.cleaned_data[
        "maximum_load_capacity"
    ]

        if capacity <= 0:
            raise forms.ValidationError(
            "Vehicle capacity must be greater than zero."
        )

        return capacity