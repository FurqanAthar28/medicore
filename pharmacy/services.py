from collections import OrderedDict
from decimal import Decimal

from django.db import transaction

from patients.models import Bill, Payment
from .models import Medicine, Sale, SaleItem


class StockError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('; '.join(errors))


def merge_items(items):
    """Combine duplicate medicines: [(medicine, qty), ...] -> {medicine_pk: qty}."""
    merged = OrderedDict()
    for medicine, quantity in items:
        merged[medicine.pk] = merged.get(medicine.pk, 0) + quantity
    return merged


def stock_errors(medicines, quantities):
    errors = []
    for pk, quantity in quantities.items():
        medicine = medicines[pk]
        if not medicine.is_active:
            errors.append(f"{medicine.name} is no longer sold.")
        elif medicine.is_expired:
            errors.append(f"{medicine.name} is expired and cannot be sold.")
        elif medicine.stock_quantity < quantity:
            errors.append(f"Only {medicine.stock_quantity} of {medicine.name} left in stock (requested {quantity}).")
    return errors


@transaction.atomic
def create_sale(patient, items, user, prescription=None, payment_method=None):
    """
    Sell medicines to a patient: deduct stock, record the sale and raise a bill.
    If payment_method is given the bill is paid in full immediately.
    """
    quantities = merge_items(items)
    if not quantities:
        raise StockError(["Add at least one medicine."])

    # Lock the medicine rows so concurrent sales can't oversell stock
    medicines = Medicine.objects.select_for_update().in_bulk(list(quantities))
    errors = stock_errors(medicines, quantities)
    if errors:
        raise StockError(errors)

    sale = Sale.objects.create(patient=patient, prescription=prescription, sold_by=user)
    total = Decimal('0')
    lines = []
    for pk, quantity in quantities.items():
        medicine = medicines[pk]
        SaleItem.objects.create(sale=sale, medicine=medicine, quantity=quantity, unit_price=medicine.unit_price)
        medicine.stock_quantity -= quantity
        medicine.save(update_fields=['stock_quantity'])
        total += medicine.unit_price * quantity
        lines.append(f"{medicine.name} x {quantity} @ {medicine.unit_price}")

    bill = Bill.objects.create(
        patient=patient,
        total_amount=total,
        description=f"Pharmacy sale #{sale.id}\n" + "\n".join(lines),
    )
    sale.total_amount = total
    sale.bill = bill
    sale.save(update_fields=['total_amount', 'bill'])

    if payment_method:
        Payment.objects.create(bill=bill, amount=total, payment_method=payment_method, received_by=user)
    return sale
