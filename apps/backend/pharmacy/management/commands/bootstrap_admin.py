"""Bootstrap the local coursework administrator without replacing existing users."""
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone
from pharmacy.models import Users


class Command(BaseCommand):
    help = "Create admin / admin only when no ADMIN account exists (local coursework)."

    def handle(self, *args, **options):
        # Serialize simultaneous startup attempts without adding schema objects.
        with connection.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 10)", ["internet_pharmacy.bootstrap_admin"])
            if cursor.fetchone()[0] != 1:
                raise CommandError("Could not acquire administrator bootstrap lock.")
            try:
                if Users.objects.filter(role="ADMIN").exists():
                    self.stdout.write("Administrator already exists; no account changed.")
                    return
                if Users.objects.filter(username="admin").exists():
                    raise CommandError("Username admin belongs to a non-admin account; resolve the collision explicitly.")
                if Users.objects.filter(email="admin@localhost.test").exists():
                    raise CommandError("Bootstrap email admin@localhost.test is already in use; no account changed.")
                user = Users.objects.create(
                    username="admin", email="admin@localhost.test",
                    password=make_password("admin"), role="ADMIN",
                    is_staff=True, is_active=True, created_at=timezone.now(),
                )
                self.stdout.write(self.style.SUCCESS(f"Created initial administrator admin (id={user.id})."))
            finally:
                cursor.execute("SELECT RELEASE_LOCK(%s)", ["internet_pharmacy.bootstrap_admin"])
