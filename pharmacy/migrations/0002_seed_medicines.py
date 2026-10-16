from decimal import Decimal

from django.db import migrations

from pharmacy.seed_data import MEDICINES


def add_medicines(apps, schema_editor):
    Medicine = apps.get_model('pharmacy', 'Medicine')
    for name, generic, form, manufacturer, price, stock in MEDICINES:
        # get_or_create: never touches medicines that already exist
        Medicine.objects.get_or_create(
            name=name,
            defaults={
                'generic_name': generic,
                'form': form,
                'manufacturer': manufacturer,
                'unit_price': Decimal(price),
                'stock_quantity': stock,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0001_initial'),
    ]

    operations = [
        # Reverse is a no-op so rolling back never deletes pharmacy stock
        migrations.RunPython(add_medicines, migrations.RunPython.noop),
    ]
