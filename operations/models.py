from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from fleet.models import *


class Trip(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        DISPATCHED = "DISPATCHED", "Dispatched"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    source = models.CharField(
        max_length=150,
    )

    destination = models.CharField(
        max_length=150,
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="trips",
    )

    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="trips",
    )

    cargo_weight = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        help_text="Cargo weight in kilograms.",
    )

    planned_distance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        help_text="Planned distance in kilometres.",
    )

    start_odometer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    final_odometer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    fuel_consumed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        help_text="Fuel consumed in litres.",
    )

    revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
    )

    notes = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_trips",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    dispatched_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["vehicle", "status"]),
            models.Index(fields=["driver", "status"]),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(cargo_weight__gt=0),
                name="trip_cargo_weight_positive",
            ),

            models.CheckConstraint(
                condition=Q(planned_distance__gt=0),
                name="trip_distance_positive",
            ),

            models.CheckConstraint(
                condition=Q(revenue__gte=0),
                name="trip_revenue_non_negative",
            ),

            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(status="DISPATCHED"),
                name="one_active_trip_per_vehicle",
            ),

            models.UniqueConstraint(
                fields=["driver"],
                condition=Q(status="DISPATCHED"),
                name="one_active_trip_per_driver",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.vehicle_id
            and self.cargo_weight
            and self.cargo_weight
            > self.vehicle.maximum_load_capacity
        ):
            errors["cargo_weight"] = (
                f"Cargo weight cannot exceed "
                f"{self.vehicle.maximum_load_capacity} kg."
            )

        if (
            self.start_odometer is not None
            and self.final_odometer is not None
            and self.final_odometer < self.start_odometer
        ):
            errors["final_odometer"] = (
                "Final odometer cannot be less "
                "than starting odometer."
            )

        if (
            self.source
            and self.destination
            and self.source.strip().lower()
            == self.destination.strip().lower()
        ):
            errors["destination"] = (
                "Source and destination cannot be the same."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def actual_distance(self):
        if (
            self.start_odometer is None
            or self.final_odometer is None
        ):
            return None

        return self.final_odometer - self.start_odometer

    @property
    def fuel_efficiency(self):
        if (
            self.actual_distance is None
            or not self.fuel_consumed
        ):
            return None

        return self.actual_distance / self.fuel_consumed

    def __str__(self):
        return (
            f"Trip #{self.pk}: "
            f"{self.source} → {self.destination}"
        )
    
class MaintenanceRecord(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="maintenance_records",
    )

    maintenance_type = models.CharField(
        max_length=120,
    )

    description = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    estimated_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )

    final_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )

    expected_completion_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )

    completion_notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_maintenance_records",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["vehicle", "status"]),
            models.Index(fields=["priority"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(status="IN_PROGRESS"),
                name="one_active_maintenance_per_vehicle",
            ),
        ]

    def __str__(self):
        return (
            f"{self.vehicle.registration_number} - "
            f"{self.maintenance_type}"
        )


class FuelLog(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="fuel_logs",
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.PROTECT,
        related_name="fuel_logs",
        null=True,
        blank=True,
    )

    date = models.DateField(
        default=timezone.localdate,
    )

    liters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    price_per_liter = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    total_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        editable=False,
    )

    odometer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_fuel_logs",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-date", "-created_at"]

        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["vehicle"]),
        ]

    def clean(self):
        errors = {}

        if (
            self.trip_id
            and self.vehicle_id
            and self.trip.vehicle_id != self.vehicle_id
        ):
            errors["trip"] = (
                "The selected trip does not belong "
                "to the selected vehicle."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.total_cost = self.liters * self.price_per_liter

        update_fields = kwargs.get("update_fields")

        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "total_cost",
            }

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.vehicle.registration_number} - "
            f"{self.liters} L"
        )


class Expense(models.Model):
    class ExpenseType(models.TextChoices):
        TOLL = "TOLL", "Toll"
        PARKING = "PARKING", "Parking"
        DRIVER_ALLOWANCE = (
            "DRIVER_ALLOWANCE",
            "Driver Allowance",
        )
        REPAIR = "REPAIR", "Repair"
        INSURANCE = "INSURANCE", "Insurance"
        PERMIT = "PERMIT", "Permit"
        OTHER = "OTHER", "Other"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="expenses",
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.PROTECT,
        related_name="expenses",
        null=True,
        blank=True,
    )

    expense_type = models.CharField(
        max_length=30,
        choices=ExpenseType.choices,
        default=ExpenseType.OTHER,
    )

    description = models.CharField(
        max_length=255,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    date = models.DateField(
        default=timezone.localdate,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_expenses",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-date", "-created_at"]

        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["vehicle"]),
            models.Index(fields=["expense_type"]),
        ]

    def clean(self):
        if (
            self.trip_id
            and self.vehicle_id
            and self.trip.vehicle_id != self.vehicle_id
        ):
            raise ValidationError(
                {
                    "trip": (
                        "The selected trip does not belong "
                        "to the selected vehicle."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.get_expense_type_display()} - "
            f"₹{self.amount}"
        )