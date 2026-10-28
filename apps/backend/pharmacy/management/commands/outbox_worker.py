import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from pharmacy.composition import Services
from pharmacy.infrastructure.worker import OutboxWorker


class Command(BaseCommand):
    help = "Process transactional outbox events and scheduled maintenance."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--poll-seconds", type=float, default=2)

    def handle(self, *args, **options):
        worker = OutboxWorker(Services())
        while True:
            close_old_connections()
            worker.maintenance()
            count = 0
            for _ in range(max(1, options["batch_size"])):
                if not worker.process_one():
                    break
                count += 1
            if options["once"]:
                self.stdout.write(f"Processed {count} events")
                return
            time.sleep(max(0.1, options["poll_seconds"]))
