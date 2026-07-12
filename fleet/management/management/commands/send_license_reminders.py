from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from fleet.models import Driver


class Command(BaseCommand):
    help = "Email a consolidated reminder for driver licences nearing expiry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=getattr(settings, "LICENSE_REMINDER_DAYS", 30),
            help="Include licences expiring within this many days.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days < 0:
            raise CommandError("--days cannot be negative.")

        today = timezone.localdate()
        deadline = today + timedelta(days=days)

        drivers = Driver.objects.filter(
            license_expiry_date__gte=today,
            license_expiry_date__lte=deadline,
        ).order_by("license_expiry_date", "name")

        if not drivers.exists():
            self.stdout.write(
                self.style.SUCCESS("No expiring licences found.")
            )
            return

        recipients = list(
            User.objects.filter(
                is_active=True,
                role__in=[
                    User.Role.ADMIN,
                    User.Role.SAFETY_OFFICER,
                ],
            )
            .exclude(email="")
            .values_list("email", flat=True)
            .distinct()
        )

        configured_recipients = getattr(
            settings,
            "LICENSE_REMINDER_RECIPIENTS",
            [],
        )
        recipients = sorted(set(recipients + configured_recipients))

        if not recipients:
            raise CommandError(
                "No active Admin/Safety Officer email recipients were found."
            )

        lines = [
            "TransitOps Driver Licence Expiry Reminder",
            "",
            f"The following licences expire between {today} and {deadline}:",
            "",
        ]

        for driver in drivers:
            remaining = (driver.license_expiry_date - today).days
            lines.append(
                f"- {driver.name} | {driver.license_number} | "
                f"expires {driver.license_expiry_date} | "
                f"{remaining} day(s) remaining"
            )

        lines.extend(
            [
                "",
                "Open TransitOps and update the driver record before expiry.",
            ]
        )

        sent_count = send_mail(
            subject=f"TransitOps: {drivers.count()} licence(s) expiring soon",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Reminder generated for {drivers.count()} driver(s); "
                f"email delivery count: {sent_count}."
            )
        )
