from django.urls import path

from . import views


app_name = "operations"


urlpatterns = [
    path(
        "trips/",
        views.trip_list,
        name="trip_list",
    ),

    path(
        "trips/create/",
        views.trip_create,
        name="trip_create",
    ),

    path(
        "trips/<int:pk>/",
        views.trip_detail,
        name="trip_detail",
    ),

    path("trips/<int:pk>/update/",views.trip_update,name="trip_update",),

    path(
        "trips/<int:pk>/dispatch/",
        views.trip_dispatch,
        name="trip_dispatch",
    ),

    path(
        "trips/<int:pk>/complete/",
        views.trip_complete,
        name="trip_complete",
    ),

    path(
        "trips/<int:pk>/cancel/",
        views.trip_cancel,
        name="trip_cancel",
    ),
    path(
    "maintenance/",
    views.maintenance_list,
    name="maintenance_list",
),

path(
    "maintenance/create/",
    views.maintenance_create,
    name="maintenance_create",
),

path(
    "maintenance/<int:pk>/",
    views.maintenance_detail,
    name="maintenance_detail",
),

path(
    "maintenance/<int:pk>/close/",
    views.maintenance_close,
    name="maintenance_close",
),

path(
    "maintenance/<int:pk>/cancel/",
    views.maintenance_cancel,
    name="maintenance_cancel",
),

path(
    "fuel-logs/",
    views.fuel_log_list,
    name="fuel_log_list",
),

path(
    "fuel-logs/create/",
    views.fuel_log_create,
    name="fuel_log_create",
),

path(
    "fuel-logs/<int:pk>/update/",
    views.fuel_log_update,
    name="fuel_log_update",
),

path(
    "fuel-logs/<int:pk>/delete/",
    views.fuel_log_delete,
    name="fuel_log_delete",
),

path(
    "expenses/",
    views.expense_list,
    name="expense_list",
),

path(
    "expenses/create/",
    views.expense_create,
    name="expense_create",
),

path(
    "expenses/<int:pk>/update/",
    views.expense_update,
    name="expense_update",
),

path(
    "expenses/<int:pk>/delete/",
    views.expense_delete,
    name="expense_delete",
),  
path(
    "reports/",
    views.reports_dashboard,
    name="reports_dashboard",
),

path(
    "reports/export/csv/",
    views.export_vehicle_report_csv,
    name="export_vehicle_report_csv",
),
]