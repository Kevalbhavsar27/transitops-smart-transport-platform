from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from fleet.models import Driver


class Command(BaseCommand):
    help = (
        "Send email reminders for driver licences "
        "that will expire within a selected number of days."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help=(
                "Number of days ahead to check. "
                "Defaults to LICENSE_REMINDER_DAYS from settings."
            ),
        )

    def handle(self, *args, **options):
        configured_days = getattr(
            settings,
            "LICENSE_REMINDER_DAYS",
            30,
        )

        days = (
            options["days"]
            if options["days"] is not None
            else configured_days
        )

        if days < 0:
            self.stderr.write(
                self.style.ERROR(
                    "--days cannot be negative."
                )
            )
            return

        today = timezone.localdate()
        expiry_limit = today + timedelta(days=days)

        drivers = Driver.objects.filter(
            license_expiry_date__gte=today,
            license_expiry_date__lte=expiry_limit,
        ).order_by(
            "license_expiry_date",
            "name",
        )

        if not drivers.exists():
            self.stdout.write(
                self.style.SUCCESS(
                    f"No driver licences expire within {days} days."
                )
            )
            return

        recipients = self.get_recipients()

        if not recipients:
            self.stderr.write(
                self.style.WARNING(
                    "Expiring licences were found, but no reminder "
                    "recipient email addresses are configured."
                )
            )

            self.print_expiring_drivers(
                drivers,
                today,
            )
            return

        subject = (
            f"TransitOps: {drivers.count()} driver "
            f"licence expiry reminder"
        )

        message = self.build_email_message(
            drivers=drivers,
            today=today,
            expiry_limit=expiry_limit,
            days=days,
        )

        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                "TransitOps <transitops@localhost>",
            ),
            recipient_list=recipients,
            fail_silently=False,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Reminder processed successfully. "
                f"Drivers: {drivers.count()}, "
                f"recipients: {len(recipients)}, "
                f"emails sent: {sent_count}."
            )
        )

    def get_recipients(self):
        """
        Get recipients from settings and active Admin/Safety Officer users.
        Duplicate addresses are removed.
        """
        recipients = list(
            getattr(
                settings,
                "LICENSE_REMINDER_RECIPIENTS",
                [],
            )
        )

        role_recipients = (
            User.objects
            .filter(
                is_active=True,
                role__in=[
                    User.Role.ADMIN,
                    User.Role.SAFETY_OFFICER,
                ],
            )
            .exclude(email="")
            .values_list("email", flat=True)
        )

        recipients.extend(role_recipients)

        # Remove blank and duplicate addresses.
        return list(
            dict.fromkeys(
                email.strip()
                for email in recipients
                if email and email.strip()
            )
        )

    def build_email_message(
        self,
        drivers,
        today,
        expiry_limit,
        days,
    ):
        lines = [
            "TransitOps Driver Licence Expiry Reminder",
            "",
            (
                f"The following driver licences expire "
                f"between {today:%d %b %Y} and "
                f"{expiry_limit:%d %b %Y} "
                f"({days} day window):"
            ),
            "",
        ]

        for driver in drivers:
            remaining_days = (
                driver.license_expiry_date - today
            ).days

            lines.extend(
                [
                    f"Driver: {driver.name}",
                    f"Licence: {driver.license_number}",
                    f"Category: {driver.license_category}",
                    (
                        "Expiry date: "
                        f"{driver.license_expiry_date:%d %b %Y}"
                    ),
                    f"Days remaining: {remaining_days}",
                    f"Current status: {driver.get_status_display()}",
                    "-" * 50,
                ]
            )

        lines.extend(
            [
                "",
                (
                    "Please renew the affected licences before "
                    "assigning these drivers to future trips."
                ),
                "",
                "TransitOps",
            ]
        )

        return "\n".join(lines)

    def print_expiring_drivers(
        self,
        drivers,
        today,
    ):
        self.stdout.write(
            "Expiring driver licences:"
        )

        for driver in drivers:
            remaining_days = (
                driver.license_expiry_date - today
            ).days

            self.stdout.write(
                (
                    f"- {driver.name} | "
                    f"{driver.license_number} | "
                    f"{driver.license_expiry_date} | "
                    f"{remaining_days} day(s) remaining"
                )
            )