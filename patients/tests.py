from datetime import timedelta, time
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import AppointmentForm, BillForm, PaymentForm
from .models import Appointment, Bill, Doctor, Patient, Payment


class BaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('staff', password='pass12345')
        self.client.force_login(self.user)
        self.patient = Patient.objects.create(
            name='Ali', age=30, gender='Male', phone='03001234567', address='Lahore',
        )
        self.doctor = Doctor.objects.create(
            name='Sara', specialization='Cardiology', phone='03007654321', email='sara@example.com',
        )


class AuthTests(BaseTestCase):
    def test_logout_via_post(self):
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('patients:patient_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_all_pages_render(self):
        bill = Bill.objects.create(patient=self.patient, total_amount=Decimal('100'))
        for name, args in [
            ('patients:dashboard', []), ('patients:patient_list', []), ('patients:trash_list', []),
            ('patients:doctor_list', []), ('patients:appointment_list', []), ('patients:bill_list', []),
            ('patients:bill_detail', [bill.pk]), ('patients:add_payment', [bill.pk]),
            ('patients:create_bill', []), ('patients:create_appointment', []),
        ]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)


class PermissionTests(BaseTestCase):
    def test_non_admin_cannot_edit_doctor(self):
        response = self.client.get(reverse('patients:update_doctor', args=[self.doctor.pk]))
        self.assertRedirects(response, reverse('patients:dashboard'))

    def test_admin_group_can_edit_doctor(self):
        self.user.groups.add(Group.objects.create(name='Admin'))
        response = self.client.get(reverse('patients:update_doctor', args=[self.doctor.pk]))
        self.assertEqual(response.status_code, 200)


class PatientTests(BaseTestCase):
    def test_restore_requires_post(self):
        self.patient.is_deleted = True
        self.patient.save()
        url = reverse('patients:restore_patient', args=[self.patient.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_deleted)

    def test_deleted_patient_hidden_from_forms(self):
        self.patient.is_deleted = True
        self.patient.save()
        self.assertNotIn(self.patient, AppointmentForm().fields['patient'].queryset)
        self.assertNotIn(self.patient, BillForm().fields['patient'].queryset)


class AppointmentTests(BaseTestCase):
    def _data(self, **overrides):
        data = {
            'patient': self.patient.pk, 'doctor': self.doctor.pk,
            'appointment_date': timezone.localdate() + timedelta(days=1),
            'appointment_time': '10:00', 'status': 'Scheduled', 'notes': '',
        }
        data.update(overrides)
        return data

    def test_double_booking_rejected(self):
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.localdate() + timedelta(days=1), appointment_time=time(10, 0),
        )
        self.assertFalse(AppointmentForm(self._data()).is_valid())

    def test_cancelled_slot_can_be_rebooked(self):
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, status='Cancelled',
            appointment_date=timezone.localdate() + timedelta(days=1), appointment_time=time(10, 0),
        )
        self.assertTrue(AppointmentForm(self._data()).is_valid())

    def test_past_date_rejected_for_new(self):
        form = AppointmentForm(self._data(appointment_date=timezone.localdate() - timedelta(days=1)))
        self.assertFalse(form.is_valid())


class BillingTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.bill = Bill.objects.create(patient=self.patient, total_amount=Decimal('1000'))

    def test_status_transitions(self):
        Payment.objects.create(bill=self.bill, amount=Decimal('400'), received_by=self.user)
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, 'Partial')
        payment = Payment.objects.create(bill=self.bill, amount=Decimal('600'), received_by=self.user)
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, 'Paid')
        payment.delete()
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, 'Partial')

    def test_zero_or_negative_payment_rejected(self):
        for amount in ['0', '-50']:
            form = PaymentForm({'amount': amount, 'payment_method': 'Cash'}, bill=self.bill)
            self.assertFalse(form.is_valid(), amount)

    def test_overpayment_rejected(self):
        form = PaymentForm({'amount': '1500', 'payment_method': 'Cash'}, bill=self.bill)
        self.assertFalse(form.is_valid())

    def test_add_payment_view(self):
        self.client.post(reverse('patients:add_payment', args=[self.bill.pk]),
                         {'amount': '1000', 'payment_method': 'Card'})
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, 'Paid')

    def test_total_cannot_drop_below_paid(self):
        Payment.objects.create(bill=self.bill, amount=Decimal('800'), received_by=self.user)
        form = BillForm({'patient': self.patient.pk, 'total_amount': '500', 'description': ''},
                        instance=self.bill)
        self.assertFalse(form.is_valid())

    def test_raising_total_reverts_paid_to_partial(self):
        Payment.objects.create(bill=self.bill, amount=Decimal('1000'), received_by=self.user)
        self.client.post(reverse('patients:update_bill', args=[self.bill.pk]),
                         {'patient': self.patient.pk, 'total_amount': '1500', 'description': ''})
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, 'Partial')

    def test_dashboard_counts_partial_as_outstanding(self):
        Payment.objects.create(bill=self.bill, amount=Decimal('100'), received_by=self.user)
        response = self.client.get(reverse('patients:dashboard'))
        self.assertEqual(response.context['unpaid_bills'], 1)

    def test_invoice_pdf_with_long_content(self):
        self.bill.description = 'Long line of services ' * 50
        self.bill.save()
        for _ in range(60):
            Payment.objects.create(bill=self.bill, amount=Decimal('1'), received_by=self.user)
        response = self.client.get(reverse('patients:download_invoice', args=[self.bill.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
