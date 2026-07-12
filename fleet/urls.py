from django.urls import path

from . import views


app_name = "fleet"


urlpatterns = [
    path(
        "vehicles/",
        views.vehicle_list,
        name="vehicle_list",
    ),
    path(
        "vehicles/create/",
        views.vehicle_create,
        name="vehicle_create",
    ),
    path(
        "vehicles/<int:pk>/update/",
        views.vehicle_update,
        name="vehicle_update",
    ),
    path(
        "vehicles/<int:pk>/delete/",
        views.vehicle_delete,
        name="vehicle_delete",
    ),

    path(
        "drivers/",
        views.driver_list,
        name="driver_list",
    ),
    path(
        "drivers/create/",
        views.driver_create,
        name="driver_create",
    ),
    path(
        "drivers/<int:pk>/update/",
        views.driver_update,
        name="driver_update",
    ),
    path(
        "drivers/<int:pk>/delete/",
        views.driver_delete,
        name="driver_delete",
    ),
]