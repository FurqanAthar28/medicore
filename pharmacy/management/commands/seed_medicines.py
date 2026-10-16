from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from pharmacy.models import Medicine
from pharmacy.seed_data import MEDICINES


class Command(BaseCommand):
    help = 'Add a starter list of common medicines to the pharmacy (existing medicines are left unchanged).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--expiry', default=None,
            help='Expiry date for the new stock, YYYY-MM-DD (default: none).',
        )

    def handle(self, *args, **options):
        expiry = date.fromisoformat(options['expiry']) if options['expiry'] else None
        created = 0
        for name, generic, form, manufacturer, price, stock in MEDICINES:
            _, was_created = Medicine.objects.get_or_create(
                name=name,
                defaults={
                    'generic_name': generic,
                    'form': form,
                    'manufacturer': manufacturer,
                    'unit_price': Decimal(price),
                    'stock_quantity': stock,
                    'expiry_date': expiry,
                },
            )
            created += was_created
        skipped = len(MEDICINES) - created
        self.stdout.write(self.style.SUCCESS(
            f'Added {created} medicine(s); {skipped} already existed and were left unchanged.'
        ))
