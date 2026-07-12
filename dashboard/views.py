from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    stats = [
        {
            "title": "Active Vehicles",
            "value": 0,
            "subtitle": "Vehicles currently operating",
        },
        {
            "title": "Available Vehicles",
            "value": 0,
            "subtitle": "Ready for dispatch",
        },
        {
            "title": "Vehicles in Maintenance",
            "value": 0,
            "subtitle": "Currently in shop",
        },
        {
            "title": "Active Trips",
            "value": 0,
            "subtitle": "Trips currently dispatched",
        },
        {
            "title": "Pending Trips",
            "value": 0,
            "subtitle": "Trips waiting for dispatch",
        },
        {
            "title": "Drivers On Duty",
            "value": 0,
            "subtitle": "Drivers assigned to trips",
        },
    ]

    context = {
        "stats": stats,
        "fleet_utilization": 0,
    }

    return render(request, "dashboard/home.html", context)