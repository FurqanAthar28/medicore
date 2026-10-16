from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from pharmacy.models import Medicine

# Starter catalogue of common medicines. Prices are sample values; edit them
# from the Medicines page to match your pharmacy's real prices.
# (name, generic name, form, manufacturer, unit price, stock)
MEDICINES = [
    ('Panadol 500mg', 'Paracetamol', 'Tablet', 'GSK', '2.50', 500),
    ('Panadol Extra', 'Paracetamol + Caffeine', 'Tablet', 'GSK', '4.00', 300),
    ('Calpol Syrup 120mg/5ml', 'Paracetamol', 'Syrup', 'GSK', '95.00', 60),
    ('Brufen 400mg', 'Ibuprofen', 'Tablet', 'Abbott', '6.00', 300),
    ('Ponstan 250mg', 'Mefenamic Acid', 'Capsule', 'Pfizer', '5.50', 200),
    ('Disprin 300mg', 'Aspirin', 'Tablet', 'Reckitt', '1.50', 400),
    ('Augmentin 625mg', 'Amoxicillin + Clavulanic Acid', 'Tablet', 'GSK', '45.00', 150),
    ('Amoxil 500mg', 'Amoxicillin', 'Capsule', 'GSK', '18.00', 200),
    ('Azomax 500mg', 'Azithromycin', 'Tablet', 'Getz Pharma', '65.00', 100),
    ('Ciproxin 500mg', 'Ciprofloxacin', 'Tablet', 'Bayer', '35.00', 120),
    ('Flagyl 400mg', 'Metronidazole', 'Tablet', 'Sanofi', '4.50', 250),
    ('Velosef 500mg', 'Cephradine', 'Capsule', 'GSK', '28.00', 120),
    ('Risek 20mg', 'Omeprazole', 'Capsule', 'Getz Pharma', '15.00', 250),
    ('Motilium 10mg', 'Domperidone', 'Tablet', 'Janssen', '6.00', 200),
    ('Gaviscon Syrup', 'Sodium Alginate + Antacid', 'Syrup', 'Reckitt', '280.00', 40),
    ('ORS Sachet', 'Oral Rehydration Salts', 'Other', 'Searle', '20.00', 300),
    ('Softin 10mg', 'Loratadine', 'Tablet', 'Searle', '8.00', 200),
    ('Hydryllin Syrup', 'Diphenhydramine + Ammonium Chloride', 'Syrup', 'Searle', '120.00', 50),
    ('Ventolin Inhaler', 'Salbutamol', 'Other', 'GSK', '450.00', 30),
    ('Glucophage 500mg', 'Metformin', 'Tablet', 'Merck', '5.00', 400),
    ('Amaryl 2mg', 'Glimepiride', 'Tablet', 'Sanofi', '22.00', 150),
    ('Norvasc 5mg', 'Amlodipine', 'Tablet', 'Pfizer', '25.00', 200),
    ('Concor 5mg', 'Bisoprolol', 'Tablet', 'Merck', '20.00', 150),
    ('Lipiget 10mg', 'Atorvastatin', 'Tablet', 'Getz Pharma', '18.00', 200),
    ('Loprin 75mg', 'Aspirin (low dose)', 'Tablet', 'Highnoon', '2.00', 300),
    ('Surbex-Z', 'Multivitamin + Zinc', 'Tablet', 'Abbott', '12.00', 200),
    ('Cac-1000 Plus', 'Calcium + Vitamin C', 'Tablet', 'GSK', '25.00', 150),
    ('Polyfax Ointment', 'Polymyxin B + Bacitracin', 'Ointment', 'GSK', '180.00', 40),
    ('Betnovate Cream', 'Betamethasone', 'Ointment', 'GSK', '150.00', 40),
    ('Tobradex Eye Drops', 'Tobramycin + Dexamethasone', 'Drops', 'Novartis', '320.00', 30),
    ('Decadron Injection 4mg', 'Dexamethasone', 'Injection', 'Merck', '45.00', 60),
    ('Ceftriaxone Injection 1g', 'Ceftriaxone', 'Injection', 'Generic', '250.00', 50),
]


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
