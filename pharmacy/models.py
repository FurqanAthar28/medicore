from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Medicine(models.Model):
    FORM_CHOICES = [
        ('Tablet', 'Tablet'),
        ('Capsule', 'Capsule'),
        ('Syrup', 'Syrup'),
        ('Injection', 'Injection'),
        ('Ointment', 'Ointment'),
        ('Drops', 'Drops'),
        ('Other', 'Other'),
    ]
    name = models.CharField(max_length=200, unique=True)
    generic_name = models.CharField(max_length=200, blank=True)
    form = models.CharField(max_length=20, choices=FORM_CHOICES, default='Tablet')
    manufacturer = models.CharField(max_length=200, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level

    @property
    def is_expired(self):
        return self.expiry_date is not None and self.expiry_date < timezone.localdate()

    @property
    def is_available(self):
        return self.is_active and not self.is_expired and self.stock_quantity > 0

    def __str__(self):
        return f"{self.name} ({self.form})"


class Sale(models.Model):
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='pharmacy_sales')
    prescription = models.ForeignKey(
        'patients.Prescription', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales',
    )
    bill = models.OneToOneField(
        'patients.Bill', on_delete=models.PROTECT, null=True, blank=True, related_name='pharmacy_sale',
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pharmacy_sales')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale #{self.id} - {self.patient.name}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Price is copied at time of sale so later price changes don't alter past sales
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"
