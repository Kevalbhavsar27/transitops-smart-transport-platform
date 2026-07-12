from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from fleet.models import Driver, Vehicle
from operations.models import (
    Expense,
    FuelLog,
    MaintenanceRecord,
    Trip,
)


@login_required
def home(request):
    today = timezone.localdate()
    expiry_limit = today + timedelta(days=30)

    total_vehicles = Vehicle.objects.count()

    active_vehicles = Vehicle.objects.exclude(
        status=Vehicle.Status.RETIRED
    ).count()

    available_vehicles = Vehicle.objects.filter(
        status=Vehicle.Status.AVAILABLE
    ).count()

    vehicles_on_trip = Vehicle.objects.filter(
        status=Vehicle.Status.ON_TRIP
    ).count()

    vehicles_in_shop = Vehicle.objects.filter(
        status=Vehicle.Status.IN_SHOP
    ).count()

    active_trips = Trip.objects.filter(
        status=Trip.Status.DISPATCHED
    ).count()

    pending_trips = Trip.objects.filter(
        status=Trip.Status.DRAFT
    ).count()

    completed_trips = Trip.objects.filter(
        status=Trip.Status.COMPLETED
    ).count()

    drivers_on_duty = Driver.objects.filter(
        status=Driver.Status.ON_TRIP
    ).count()

    available_drivers = Driver.objects.filter(
        status=Driver.Status.AVAILABLE,
        license_expiry_date__gte=today,
    ).count()

    active_maintenance = MaintenanceRecord.objects.filter(
        status=MaintenanceRecord.Status.IN_PROGRESS
    ).count()

    expiring_licenses = Driver.objects.filter(
        license_expiry_date__gte=today,
        license_expiry_date__lte=expiry_limit,
    ).order_by("license_expiry_date")

    total_fuel_cost = FuelLog.objects.aggregate(
        total=Sum("total_cost")
    )["total"] or Decimal("0")

    total_other_expenses = Expense.objects.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    total_maintenance_cost = MaintenanceRecord.objects.filter(
        status=MaintenanceRecord.Status.COMPLETED
    ).aggregate(
        total=Sum("final_cost")
    )["total"] or Decimal("0")

    total_revenue = Trip.objects.filter(
        status=Trip.Status.COMPLETED
    ).aggregate(
        total=Sum("revenue")
    )["total"] or Decimal("0")

    total_operational_cost = (
        total_fuel_cost
        + total_other_expenses
        + total_maintenance_cost
    )

    estimated_profit = total_revenue - total_operational_cost

    fleet_utilization = 0

    if active_vehicles > 0:
        fleet_utilization = round(
            vehicles_on_trip / active_vehicles * 100,
            2,
        )

    stats = [
        {
            "title": "Active Vehicles",
            "value": active_vehicles,
            "subtitle": "All vehicles excluding retired",
        },
        {
            "title": "Available Vehicles",
            "value": available_vehicles,
            "subtitle": "Ready for dispatch",
        },
        {
            "title": "Vehicles On Trip",
            "value": vehicles_on_trip,
            "subtitle": "Currently dispatched",
        },
        {
            "title": "Vehicles In Maintenance",
            "value": vehicles_in_shop,
            "subtitle": "Currently in shop",
        },
        {
            "title": "Active Trips",
            "value": active_trips,
            "subtitle": "Currently dispatched",
        },
        {
            "title": "Pending Trips",
            "value": pending_trips,
            "subtitle": "Draft trips",
        },
        {
            "title": "Available Drivers",
            "value": available_drivers,
            "subtitle": "Valid and ready",
        },
        {
            "title": "Drivers On Duty",
            "value": drivers_on_duty,
            "subtitle": "Assigned to active trips",
        },
    ]

    recent_trips = (
        Trip.objects
        .select_related("vehicle", "driver")
        .order_by("-created_at")[:6]
    )

    context = {
        "stats": stats,
        "fleet_utilization": fleet_utilization,
        "completed_trips": completed_trips,
        "active_maintenance": active_maintenance,
        "expiring_licenses": expiring_licenses,
        "recent_trips": recent_trips,
        "total_fuel_cost": total_fuel_cost,
        "total_other_expenses": total_other_expenses,
        "total_maintenance_cost": total_maintenance_cost,
        "total_operational_cost": total_operational_cost,
        "total_revenue": total_revenue,
        "estimated_profit": estimated_profit,

        "vehicle_chart_labels": [
            "Available",
            "On Trip",
            "In Shop",
            "Retired",
        ],

        "vehicle_chart_values": [
            Vehicle.objects.filter(
                status=Vehicle.Status.AVAILABLE
            ).count(),

            Vehicle.objects.filter(
                status=Vehicle.Status.ON_TRIP
            ).count(),

            Vehicle.objects.filter(
                status=Vehicle.Status.IN_SHOP
            ).count(),

            Vehicle.objects.filter(
                status=Vehicle.Status.RETIRED
            ).count(),
        ],

        "trip_chart_labels": [
            "Draft",
            "Dispatched",
            "Completed",
            "Cancelled",
        ],

        "trip_chart_values": [
            Trip.objects.filter(
                status=Trip.Status.DRAFT
            ).count(),

            Trip.objects.filter(
                status=Trip.Status.DISPATCHED
            ).count(),

            Trip.objects.filter(
                status=Trip.Status.COMPLETED
            ).count(),

            Trip.objects.filter(
                status=Trip.Status.CANCELLED
            ).count(),
        ],
    }

    return render(
        request,
        "dashboard/home.html",
        context,
    )