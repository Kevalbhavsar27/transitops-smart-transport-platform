from django.contrib import admin

from .models import *


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "source",
        "destination",
        "vehicle",
        "driver",
        "cargo_weight",
        "planned_distance",
        "status",
        "created_at",
    ]

    list_filter = [
        "status",
        "created_at",
        "vehicle",
        "driver",
    ]

    search_fields = [
        "source",
        "destination",
        "vehicle__registration_number",
        "driver__name",
        "driver__license_number",
    ]

    readonly_fields = [
        "start_odometer",
        "final_odometer",
        "fuel_consumed",
        "dispatched_at",
        "completed_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    ]



@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "vehicle",
        "maintenance_type",
        "priority",
        "estimated_cost",
        "final_cost",
        "status",
        "created_at",
    ]

    list_filter = [
        "status",
        "priority",
        "created_at",
    ]

    search_fields = [
        "vehicle__registration_number",
        "maintenance_type",
        "description",
    ]


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "vehicle",
        "trip",
        "date",
        "liters",
        "price_per_liter",
        "total_cost",
        "odometer",
    ]

    list_filter = [
        "date",
        "vehicle",
    ]

    search_fields = [
        "vehicle__registration_number",
        "trip__source",
        "trip__destination",
    ]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "vehicle",
        "trip",
        "expense_type",
        "description",
        "amount",
        "date",
    ]

    list_filter = [
        "expense_type",
        "date",
        "vehicle",
    ]

    search_fields = [
        "vehicle__registration_number",
        "description",
    ]