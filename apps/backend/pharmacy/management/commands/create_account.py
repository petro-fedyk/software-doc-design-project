from getpass import getpass
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from pharmacy.models import Users


class Command(BaseCommand):
    help = (
        "Create an account in the existing users table; password is entered privately."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("email")
        parser.add_argument(
            "--role", choices=["CUSTOMER", "STAFF", "ADMIN"], default="CUSTOMER"
        )

    def handle(self, *args, **options):
        password = getpass("Password: ")
        if len(password) < 4 or password != getpass("Repeat password: "):
            raise CommandError(
                "Passwords must match and contain at least 4 characters."
            )
        if Users.objects.filter(username=options["username"]).exists():
            raise CommandError("Username already exists.")
        user = Users.objects.create(
            username=options["username"],
            email=options["email"],
            password=make_password(password),
            role=options["role"],
            is_staff=options["role"] != "CUSTOMER",
            is_active=True,
            created_at=timezone.now(),
        )
        self.stdout.write(f"Created {user.role} account id={user.id}")
