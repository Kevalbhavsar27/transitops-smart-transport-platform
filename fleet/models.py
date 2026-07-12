from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Vehicle(models.Model):
    class VehicleType(models.TextChoices):
        TRUCK = "TRUCK", "Truck"
        VAN = "VAN", "Van"
        BUS = "BUS", "Bus"
        CAR = "CAR", "Car"
        BIKE = "BIKE", "Bike"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ON_TRIP = "ON_TRIP", "On Trip"
        IN_SHOP = "IN_SHOP", "In Shop"
        RETIRED = "RETIRED", "Retired"

    registration_number = models.CharField(
        max_length=30,
        unique=True,
    )

    vehicle_name = models.CharField(
        max_length=100,
    )

    model = models.CharField(
        max_length=100,
        blank=True,
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.TRUCK,
    )

    maximum_load_capacity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Maximum cargo capacity in kilograms.",
        validators=[MinValueValidator(0)],
    )

    odometer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    acquisition_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    region = models.CharField(
        max_length=100,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["registration_number"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["vehicle_type"]),
            models.Index(fields=["region"]),
        ]

    def save(self, *args, **kwargs):
        self.registration_number = self.registration_number.upper().strip()
        super().save(*args, **kwargs)

    @property
    def can_be_dispatched(self):
        return self.status == self.Status.AVAILABLE

    def __str__(self):
        return f"{self.registration_number} - {self.vehicle_name}"


class Driver(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ON_TRIP = "ON_TRIP", "On Trip"
        OFF_DUTY = "OFF_DUTY", "Off Duty"
        SUSPENDED = "SUSPENDED", "Suspended"

    name = models.CharField(
        max_length=120,
    )

    license_number = models.CharField(
        max_length=50,
        unique=True,
    )

    license_category = models.CharField(
        max_length=50,
    )

    license_expiry_date = models.DateField()

    contact_number = models.CharField(
        max_length=20,
    )

    safety_score = models.PositiveSmallIntegerField(
        default=100,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["license_expiry_date"]),
        ]

    def save(self, *args, **kwargs):
        self.license_number = self.license_number.upper().strip()
        super().save(*args, **kwargs)

    @property
    def is_license_expired(self):
        return self.license_expiry_date < timezone.localdate()

    @property
    def can_be_dispatched(self):
        return (
            self.status == self.Status.AVAILABLE
            and not self.is_license_expired
        )

    def __str__(self):
        return f"{self.name} - {self.license_number}"