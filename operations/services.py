from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from fleet.models import *

from .models import *


@transaction.atomic
def dispatch_trip(trip_id):
    trip = (
        Trip.objects
        .select_for_update()
        .select_related("vehicle", "driver")
        .get(pk=trip_id)
    )

    vehicle = Vehicle.objects.select_for_update().get(
        pk=trip.vehicle_id
    )

    driver = Driver.objects.select_for_update().get(
        pk=trip.driver_id
    )

    if trip.status != Trip.Status.DRAFT:
        raise ValidationError(
            "Only a Draft trip can be dispatched."
        )

    if vehicle.status != Vehicle.Status.AVAILABLE:
        raise ValidationError(
            "The selected vehicle is not available."
        )

    if driver.status != Driver.Status.AVAILABLE:
        raise ValidationError(
            "The selected driver is not available."
        )

    if driver.is_license_expired:
        raise ValidationError(
            "The selected driver's licence has expired."
        )

    if driver.status == Driver.Status.SUSPENDED:
        raise ValidationError(
            "A suspended driver cannot be dispatched."
        )

    if trip.cargo_weight > vehicle.maximum_load_capacity:
        raise ValidationError(
            (
                f"Cargo weight exceeds vehicle capacity of "
                f"{vehicle.maximum_load_capacity} kg."
            )
        )

    vehicle_conflict = Trip.objects.filter(
        vehicle=vehicle,
        status=Trip.Status.DISPATCHED,
    ).exclude(pk=trip.pk).exists()

    if vehicle_conflict:
        raise ValidationError(
            "This vehicle is already assigned to another active trip."
        )

    driver_conflict = Trip.objects.filter(
        driver=driver,
        status=Trip.Status.DISPATCHED,
    ).exclude(pk=trip.pk).exists()

    if driver_conflict:
        raise ValidationError(
            "This driver is already assigned to another active trip."
        )

    trip.status = Trip.Status.DISPATCHED
    trip.start_odometer = vehicle.odometer
    trip.dispatched_at = timezone.now()

    vehicle.status = Vehicle.Status.ON_TRIP
    driver.status = Driver.Status.ON_TRIP

    vehicle.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    driver.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    trip.save(
        update_fields=[
            "status",
            "start_odometer",
            "dispatched_at",
            "updated_at",
        ]
    )

    return trip


@transaction.atomic
def complete_trip(
    trip_id,
    final_odometer,
    fuel_consumed,
):
    trip = (
        Trip.objects
        .select_for_update()
        .select_related("vehicle", "driver")
        .get(pk=trip_id)
    )

    vehicle = Vehicle.objects.select_for_update().get(
        pk=trip.vehicle_id
    )

    driver = Driver.objects.select_for_update().get(
        pk=trip.driver_id
    )

    if trip.status != Trip.Status.DISPATCHED:
        raise ValidationError(
            "Only a dispatched trip can be completed."
        )

    final_odometer = Decimal(str(final_odometer))
    fuel_consumed = Decimal(str(fuel_consumed))

    if trip.start_odometer is None:
        raise ValidationError(
            "The trip does not have a starting odometer."
        )

    if final_odometer < trip.start_odometer:
        raise ValidationError(
            (
                f"Final odometer must be at least "
                f"{trip.start_odometer} km."
            )
        )

    if fuel_consumed <= 0:
        raise ValidationError(
            "Fuel consumed must be greater than zero."
        )

    trip.final_odometer = final_odometer
    trip.fuel_consumed = fuel_consumed
    trip.status = Trip.Status.COMPLETED
    trip.completed_at = timezone.now()

    vehicle.odometer = final_odometer
    vehicle.status = Vehicle.Status.AVAILABLE

    driver.status = Driver.Status.AVAILABLE

    vehicle.save(
        update_fields=[
            "odometer",
            "status",
            "updated_at",
        ]
    )

    driver.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    trip.save(
        update_fields=[
            "final_odometer",
            "fuel_consumed",
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    return trip


@transaction.atomic
def cancel_trip(trip_id):
    trip = (
        Trip.objects
        .select_for_update()
        .select_related("vehicle", "driver")
        .get(pk=trip_id)
    )

    vehicle = Vehicle.objects.select_for_update().get(
        pk=trip.vehicle_id
    )

    driver = Driver.objects.select_for_update().get(
        pk=trip.driver_id
    )

    if trip.status not in [
        Trip.Status.DRAFT,
        Trip.Status.DISPATCHED,
    ]:
        raise ValidationError(
            "Only Draft or Dispatched trips can be cancelled."
        )

    was_dispatched = (
        trip.status == Trip.Status.DISPATCHED
    )

    trip.status = Trip.Status.CANCELLED
    trip.cancelled_at = timezone.now()

    if was_dispatched:
        vehicle.status = Vehicle.Status.AVAILABLE
        driver.status = Driver.Status.AVAILABLE

        vehicle.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        driver.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    trip.save(
        update_fields=[
            "status",
            "cancelled_at",
            "updated_at",
        ]
    )

    return trip

@transaction.atomic
def open_maintenance(
    vehicle,
    maintenance_type,
    description,
    priority,
    estimated_cost=0,
    expected_completion_date=None,
    created_by=None,
):
    locked_vehicle = Vehicle.objects.select_for_update().get(
        pk=vehicle.pk
    )

    if locked_vehicle.status == Vehicle.Status.ON_TRIP:
        raise ValidationError(
            "A vehicle currently on a trip cannot enter maintenance."
        )

    if locked_vehicle.status == Vehicle.Status.RETIRED:
        raise ValidationError(
            "A retired vehicle cannot enter maintenance."
        )

    if locked_vehicle.status == Vehicle.Status.IN_SHOP:
        raise ValidationError(
            "This vehicle already has active maintenance."
        )

    active_record_exists = MaintenanceRecord.objects.filter(
        vehicle=locked_vehicle,
        status=MaintenanceRecord.Status.IN_PROGRESS,
    ).exists()

    if active_record_exists:
        raise ValidationError(
            "This vehicle already has an active maintenance record."
        )

    record = MaintenanceRecord.objects.create(
        vehicle=locked_vehicle,
        maintenance_type=maintenance_type,
        description=description,
        priority=priority,
        estimated_cost=estimated_cost,
        expected_completion_date=expected_completion_date,
        status=MaintenanceRecord.Status.IN_PROGRESS,
        created_by=created_by,
    )

    locked_vehicle.status = Vehicle.Status.IN_SHOP
    locked_vehicle.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return record


@transaction.atomic
def close_maintenance(
    maintenance_id,
    final_cost,
    completion_notes="",
):
    record = (
        MaintenanceRecord.objects
        .select_for_update()
        .select_related("vehicle")
        .get(pk=maintenance_id)
    )

    vehicle = Vehicle.objects.select_for_update().get(
        pk=record.vehicle_id
    )

    if record.status != MaintenanceRecord.Status.IN_PROGRESS:
        raise ValidationError(
            "Only active maintenance can be completed."
        )

    final_cost = Decimal(str(final_cost))

    if final_cost < 0:
        raise ValidationError(
            "Final maintenance cost cannot be negative."
        )

    record.final_cost = final_cost
    record.completion_notes = completion_notes
    record.status = MaintenanceRecord.Status.COMPLETED
    record.completed_at = timezone.now()

    if vehicle.status != Vehicle.Status.RETIRED:
        vehicle.status = Vehicle.Status.AVAILABLE

        vehicle.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    record.save(
        update_fields=[
            "final_cost",
            "completion_notes",
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    return record


@transaction.atomic
def cancel_maintenance(maintenance_id):
    record = (
        MaintenanceRecord.objects
        .select_for_update()
        .select_related("vehicle")
        .get(pk=maintenance_id)
    )

    vehicle = Vehicle.objects.select_for_update().get(
        pk=record.vehicle_id
    )

    if record.status != MaintenanceRecord.Status.IN_PROGRESS:
        raise ValidationError(
            "Only active maintenance can be cancelled."
        )

    record.status = MaintenanceRecord.Status.CANCELLED

    if vehicle.status != Vehicle.Status.RETIRED:
        vehicle.status = Vehicle.Status.AVAILABLE

        vehicle.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    record.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return record