#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if len(sys.argv) > 1 and sys.argv[1] in {"migrate", "makemigrations", "flush"}:
        sys.exit(
            "Schema ownership belongs to db/migrations/*.sql; this command is disabled."
        )
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
