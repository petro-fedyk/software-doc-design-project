"""Set the local coursework administrator password explicitly."""
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from pharmacy.models import Users


class Command(BaseCommand):
    help = "Set the coursework admin account password to admin."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 10)", ["internet_pharmacy.bootstrap_admin"])
            if cursor.fetchone()[0] != 1:
                raise CommandError("Could not acquire administrator bootstrap lock.")
            try:
                with transaction.atomic():
                    user = Users.objects.select_for_update().filter(username="admin").first()
                    if user is None:
                        raise CommandError("Username admin does not exist; run bootstrap_admin first.")
                    if user.role != "ADMIN":
                        raise CommandError("Username admin is not an ADMIN account; no account changed.")
                    user.password = make_password("admin")
                    user.is_active = True
                    user.is_staff = True
                    user.updated_at = timezone.now()
                    user.save(update_fields=["password", "is_active", "is_staff", "updated_at"])
                self.stdout.write(self.style.SUCCESS("Password updated for admin."))
            finally:
                cursor.execute("SELECT RELEASE_LOCK(%s)", ["internet_pharmacy.bootstrap_admin"])
