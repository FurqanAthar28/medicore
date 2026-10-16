from datetime import timedelta, time
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import AppointmentForm, BillForm, PaymentForm
from .models import Appointment, Bill, Doctor, Patient, Payment, Prescription


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


class DoctorPortalTests(TestCase):
    def setUp(self):
        from pharmacy.models import Medicine
        self.doctor_user = User.objects.create_user('drsara', password='pass12345')
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, name='Sara', specialization='Cardiology',
            phone='03007654321', email='sara@example.com',
        )
        self.other_doctor = Doctor.objects.create(
            name='Omar', specialization='ENT', phone='03001112222', email='omar@example.com',
        )
        self.patient = Patient.objects.create(
            name='Ali', age=30, gender='Male', phone='03001234567', address='Lahore',
        )
        self.medicine = Medicine.objects.create(name='Panadol', unit_price=Decimal('5'), stock_quantity=100)
        self.client.force_login(self.doctor_user)

    def _rx_data(self, **overrides):
        data = {
            'patient': self.patient.pk, 'diagnosis': 'Fever', 'notes': '',
            'items-TOTAL_FORMS': '1', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1', 'items-MAX_NUM_FORMS': '1000',
            'items-0-medicine': self.medicine.pk, 'items-0-quantity': '10',
            'items-0-dosage': '1 tablet twice daily', 'items-0-duration': '5 days', 'items-0-DELETE': '',
        }
        data.update(overrides)
        return data

    def test_dashboard_shows_doctor_portal(self):
        response = self.client.get(reverse('patients:dashboard'))
        self.assertTemplateUsed(response, 'dashboard/doctor_dashboard.html')

    def test_doctor_can_select_patient(self):
        response = self.client.get(reverse('patients:patient_list'), {'q': 'Ali'})
        self.assertContains(response, reverse('patients:patient_detail', args=[self.patient.pk]))
        response = self.client.get(reverse('patients:patient_detail', args=[self.patient.pk]))
        self.assertContains(response, 'Write Prescription')

    def test_doctor_writes_prescription_as_self(self):
        # Even if a different doctor is posted, the logged-in doctor is used
        response = self.client.post(reverse('patients:create_prescription'),
                                    self._rx_data(doctor=self.other_doctor.pk))
        prescription = Prescription.objects.get()
        self.assertRedirects(response, reverse('patients:prescription_detail', args=[prescription.pk]))
        self.assertEqual(prescription.doctor, self.doctor)
        self.assertEqual(prescription.items.get().quantity, 10)

    def test_prescription_requires_a_medicine(self):
        response = self.client.post(reverse('patients:create_prescription'),
                                    self._rx_data(**{'items-0-DELETE': 'on'}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Prescription.objects.exists())

    def test_consult_from_appointment_completes_it(self):
        appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.localdate(), appointment_time=time(9, 0),
        )
        self.client.post(reverse('patients:create_prescription') + f'?appointment={appointment.pk}', self._rx_data())
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'Completed')
        self.assertEqual(Prescription.objects.get().appointment, appointment)

    def test_doctor_sees_only_own_appointments(self):
        mine = Appointment.objects.create(patient=self.patient, doctor=self.doctor,
                                          appointment_date=timezone.localdate(), appointment_time=time(9, 0))
        other = Appointment.objects.create(patient=self.patient, doctor=self.other_doctor,
                                           appointment_date=timezone.localdate(), appointment_time=time(9, 0))
        response = self.client.get(reverse('patients:appointment_list'))
        self.assertIn(mine, response.context['appointments'])
        self.assertNotIn(other, response.context['appointments'])
        response = self.client.get(reverse('patients:update_appointment', args=[other.pk]))
        self.assertRedirects(response, reverse('patients:appointment_list'))

    def test_doctor_profile_access(self):
        self.assertEqual(self.client.get(reverse('patients:doctor_detail', args=[self.doctor.pk])).status_code, 200)
        response = self.client.get(reverse('patients:doctor_detail', args=[self.other_doctor.pk]))
        self.assertRedirects(response, reverse('patients:dashboard'))

    def test_non_doctor_staff_cannot_prescribe(self):
        self.client.force_login(User.objects.create_user('nurse', password='pass12345'))
        response = self.client.get(reverse('patients:create_prescription'))
        self.assertRedirects(response, reverse('patients:dashboard'))


class DoctorRegistrationTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser('admin', password='pass12345')
        self.client.force_login(admin)

    def test_register_doctor_with_login(self):
        self.client.post(reverse('patients:register_doctor'), {
            'name': 'Hina', 'specialization': 'GP', 'phone': '03001231234', 'email': 'hina@example.com',
            'username': 'drhina', 'password': 'Str0ng-Passw0rd!',
        })
        doctor = Doctor.objects.get(name='Hina')
        self.assertEqual(doctor.user.username, 'drhina')
        self.assertTrue(doctor.user.check_password('Str0ng-Passw0rd!'))

    def test_username_without_password_rejected(self):
        response = self.client.post(reverse('patients:register_doctor'), {
            'name': 'Hina', 'specialization': 'GP', 'phone': '03001231234', 'email': 'hina@example.com',
            'username': 'drhina', 'password': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Doctor.objects.exists())
