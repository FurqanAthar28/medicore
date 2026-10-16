from django import forms
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import Patient, Doctor, Appointment, Bill, Payment


phone_validator = RegexValidator(
    regex=r'^\+?[0-9\s\-()]{7,20}$',
    message='Enter a valid phone number (digits, spaces, dashes, optional leading +).',
)


def active_patients():
    return Patient.objects.filter(is_deleted=False).order_by('name')


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'age', 'gender', 'phone', 'address', 'medical_history']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Medical history (optional)'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        phone_validator(phone)
        return phone


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialization', 'phone', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cardiologist'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        phone_validator(phone)
        return phone


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        patients = active_patients()
        if self.instance.pk:
            # Keep the current patient selectable even if they were moved to trash
            patients = patients | Patient.objects.filter(pk=self.instance.patient_id)
        self.fields['patient'].queryset = patients.distinct()
        self.fields['doctor'].queryset = Doctor.objects.order_by('name')

    def clean(self):
        cleaned = super().clean()
        doctor = cleaned.get('doctor')
        date = cleaned.get('appointment_date')
        time = cleaned.get('appointment_time')
        status = cleaned.get('status')
        if not (doctor and date and time):
            return cleaned

        is_new = self.instance.pk is None
        if is_new and date < timezone.localdate():
            self.add_error('appointment_date', 'Appointment date cannot be in the past.')

        if status != 'Cancelled':
            clash = Appointment.objects.filter(
                doctor=doctor, appointment_date=date, appointment_time=time,
            ).exclude(status='Cancelled').exclude(pk=self.instance.pk)
            if clash.exists():
                raise forms.ValidationError(
                    f"Dr. {doctor.name} already has an appointment on {date} at {time.strftime('%H:%M')}."
                )
        return cleaned


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['patient', 'total_amount', 'description']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Bill description'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        patients = active_patients()
        if self.instance.pk:
            patients = patients | Patient.objects.filter(pk=self.instance.patient_id)
        self.fields['patient'].queryset = patients.distinct()
        self.fields['total_amount'].widget.attrs['placeholder'] = f'Amount in {settings.CURRENCY_SYMBOL}'

    def clean_total_amount(self):
        total = self.cleaned_data['total_amount']
        if self.instance.pk and total < self.instance.amount_paid:
            raise forms.ValidationError(
                f"Total cannot be less than the amount already paid ({self.instance.amount_paid})."
            )
        return total


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.bill = kwargs.pop('bill', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if self.bill and self.bill.balance <= 0:
            raise forms.ValidationError("This bill is already fully paid.")
        if self.bill and amount > self.bill.balance:
            raise forms.ValidationError(f"Amount cannot exceed balance of {self.bill.balance}")
        return amount