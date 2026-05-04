"""
Management command: create_admin_user

Creates a Farmers.Farmer account with role='admin' and is_approved=True.

Usage:
    python manage.py create_admin_user
    python manage.py create_admin_user --username myadmin --email admin@example.com --password secret123

If --password is omitted the command prompts for one interactively.
If the username already exists the command exits cleanly without error.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create a test admin user (role=admin, is_approved=True)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="testadmin",
            help="Username for the new admin (default: testadmin)",
        )
        parser.add_argument(
            "--email",
            default="testadmin@1847ventures.com",
            help="Email address for the new admin",
        )
        parser.add_argument(
            "--password",
            default=None,
            help="Password (prompted interactively if omitted)",
        )

    def handle(self, *args, **options):
        # Import here to avoid issues before migrations run
        from Farmers.models import Farmer, UserProfile

        username = options["username"]
        email = options["email"]
        password = options["password"]

        if Farmer.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"User '{username}' already exists — skipping creation."
                )
            )
            return

        if not password:
            import getpass
            password = getpass.getpass(f"Password for '{username}': ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise CommandError("Passwords do not match.")

        with transaction.atomic():
            user = Farmer.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            # Profile is auto-created by signal; update role + approval
            profile = user.profile
            profile.role = "admin"
            profile.is_approved = True
            profile.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin user '{username}' created successfully.\n"
                f"  Email   : {email}\n"
                f"  Role    : admin\n"
                f"  Approved: True\n"
                f"\nLogin at /api/farmers/login/ and you will be redirected to the admin dashboard."
            )
        )
