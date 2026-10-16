from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from patients.models import Bill, Doctor, Patient, Prescription, PrescriptionItem
from .models import Medicine, Sale
from .services import StockError, create_sale


class PharmacyTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('staff', password='pass12345')
        self.client.force_login(self.user)
        self.patient = Patient.objects.create(
            name='Ali', age=30, gender='Male', phone='03001234567', address='Lahore',
        )
        self.panadol = Medicine.objects.create(name='Panadol', unit_price=Decimal('5.50'), stock_quantity=100)
        self.brufen = Medicine.objects.create(name='Brufen', unit_price=Decimal('12'), stock_quantity=3)

    def sale_data(self, rows, **extra):
        data = {
            'patient': self.patient.pk, 'payment_method': '',
            'items-TOTAL_FORMS': str(len(rows)), 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1', 'items-MAX_NUM_FORMS': '1000',
        }
        for i, (medicine, quantity) in enumerate(rows):
            data[f'items-{i}-medicine'] = medicine.pk
            data[f'items-{i}-quantity'] = str(quantity)
            data[f'items-{i}-DELETE'] = ''
        data.update(extra)
        return data


class SaleServiceTests(PharmacyTestCase):
    def test_sale_deducts_stock_and_creates_bill(self):
        sale = create_sale(self.patient, [(self.panadol, 10), (self.brufen, 2)], self.user)
        self.panadol.refresh_from_db()
        self.brufen.refresh_from_db()
        self.assertEqual(self.panadol.stock_quantity, 90)
        self.assertEqual(self.brufen.stock_quantity, 1)
        self.assertEqual(sale.total_amount, Decimal('79.00'))
        self.assertEqual(sale.bill.total_amount, Decimal('79.00'))
        self.assertEqual(sale.bill.status, 'Unpaid')

    def test_pay_now_marks_bill_paid(self):
        sale = create_sale(self.patient, [(self.panadol, 2)], self.user, payment_method='Cash')
        sale.bill.refresh_from_db()
        self.assertEqual(sale.bill.status, 'Paid')

    def test_duplicate_rows_are_merged(self):
        sale = create_sale(self.patient, [(self.panadol, 2), (self.panadol, 3)], self.user)
        self.assertEqual(sale.items.get().quantity, 5)

    def test_insufficient_stock_rolls_back(self):
        with self.assertRaises(StockError):
            create_sale(self.patient, [(self.panadol, 5), (self.brufen, 10)], self.user)
        self.panadol.refresh_from_db()
        self.assertEqual(self.panadol.stock_quantity, 100)
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(Bill.objects.exists())

    def test_expired_medicine_cannot_be_sold(self):
        self.panadol.expiry_date = timezone.localdate() - timedelta(days=1)
        self.panadol.save()
        with self.assertRaises(StockError):
            create_sale(self.patient, [(self.panadol, 1)], self.user)

    def test_price_change_does_not_alter_past_sale(self):
        sale = create_sale(self.patient, [(self.panadol, 2)], self.user)
        self.panadol.unit_price = Decimal('99')
        self.panadol.save()
        self.assertEqual(sale.items.get().line_total, Decimal('11.00'))


class SaleViewTests(PharmacyTestCase):
    def test_sell_medicines(self):
        response = self.client.post(reverse('pharmacy:sale_create'), self.sale_data([(self.panadol, 4)]))
        sale = Sale.objects.get()
        self.assertRedirects(response, reverse('pharmacy:sale_detail', args=[sale.pk]))
        self.assertEqual(sale.total_amount, Decimal('22.00'))

    def test_over_stock_shows_error(self):
        response = self.client.post(reverse('pharmacy:sale_create'), self.sale_data([(self.brufen, 5)]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only 3 of Brufen left in stock')
        self.assertFalse(Sale.objects.exists())

    def test_removed_row_is_ignored(self):
        data = self.sale_data([(self.panadol, 1), (self.brufen, 50)], **{'items-1-DELETE': 'on'})
        self.client.post(reverse('pharmacy:sale_create'), data)
        self.assertEqual(Sale.objects.get().items.count(), 1)

    def test_doctor_buys_prescription_from_pharmacy(self):
        doctor_user = User.objects.create_user('drsara', password='pass12345')
        doctor = Doctor.objects.create(user=doctor_user, name='Sara', specialization='GP',
                                       phone='03007654321', email='s@example.com')
        prescription = Prescription.objects.create(patient=self.patient, doctor=doctor, diagnosis='Flu')
        PrescriptionItem.objects.create(prescription=prescription, medicine=self.panadol,
                                        quantity=6, dosage='1 tab')
        self.client.force_login(doctor_user)

        url = reverse('pharmacy:sale_create') + f'?prescription={prescription.pk}'
        response = self.client.get(url)
        self.assertEqual(response.context['formset'].initial, [{'medicine': self.panadol.pk, 'quantity': 6}])

        data = self.sale_data([(self.panadol, 6)], **{'items-INITIAL_FORMS': '1'})
        self.client.post(url, data)
        sale = Sale.objects.get()
        self.assertEqual(sale.prescription, prescription)
        self.assertTrue(prescription.is_dispensed)

    def test_pages_render(self):
        sale = create_sale(self.patient, [(self.panadol, 1)], self.user)
        for url in [reverse('pharmacy:medicine_list'), reverse('pharmacy:sale_list'),
                    reverse('pharmacy:sale_create'), reverse('pharmacy:sale_detail', args=[sale.pk]),
                    reverse('patients:bill_detail', args=[sale.bill.pk])]:
            self.assertEqual(self.client.get(url).status_code, 200, url)


class MedicinePermissionTests(PharmacyTestCase):
    def test_regular_staff_cannot_add_medicine(self):
        response = self.client.get(reverse('pharmacy:medicine_create'))
        self.assertRedirects(response, reverse('patients:dashboard'))

    def test_pharmacist_can_add_medicine(self):
        self.user.groups.add(Group.objects.create(name='Pharmacist'))
        self.client.post(reverse('pharmacy:medicine_create'), {
            'name': 'Augmentin', 'generic_name': 'Amoxicillin', 'form': 'Tablet', 'manufacturer': '',
            'unit_price': '45', 'stock_quantity': '50', 'reorder_level': '10', 'expiry_date': '', 'is_active': 'on',
        })
        self.assertTrue(Medicine.objects.filter(name='Augmentin').exists())
