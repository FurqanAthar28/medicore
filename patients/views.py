from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Patient, Doctor, Appointment, Bill
from .forms import PatientForm, DoctorForm, AppointmentForm, BillForm, PaymentForm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from functools import wraps


def group_required(*group_names):
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.groups.filter(name__in=group_names).exists() or request.user.is_superuser:
                return func(request, *args, **kwargs)
            messages.error(request, "You don't have permission to access this page.")
            return redirect('patients:dashboard')
        return wrapper
    return decorator


admin_required = group_required(settings.ADMIN_GROUP_NAME)


@login_required
def dashboard(request):
    total_patients = Patient.objects.filter(is_deleted=False).count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()
    # Bills that still have money owed (Unpaid or Partial)
    unpaid_bills = Bill.objects.exclude(status='Paid').count()
    recent_appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-created_at')[:5]

    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'unpaid_bills': unpaid_bills,
        'recent_appointments': recent_appointments,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


# --- Patients ---

@login_required
def patient_list(request):
    patients = Patient.objects.filter(is_deleted=False).order_by('name')
    return render(request, 'patients/patient_list.html', {'patients': patients})


@login_required
def create_patient(request):
    form = PatientForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Patient added successfully.')
        return redirect('patients:patient_list')
    return render(request, 'patients/patient_form.html', {'form': form, 'title': 'Add Patient'})


@login_required
def update_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk, is_deleted=False)
    form = PatientForm(request.POST or None, instance=patient)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        messages.success(request, 'Patient updated successfully.')
        return redirect('patients:patient_list')
    return render(request, 'patients/patient_form.html', {'form': form, 'title': 'Update Patient'})


@login_required
def delete_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk, is_deleted=False)
    if request.method == 'POST':
        patient.is_deleted = True
        patient.deleted_at = timezone.now()
        patient.updated_by = request.user
        patient.save()
        messages.success(request, 'Patient moved to trash.')
        return redirect('patients:patient_list')
    return render(request, 'patients/confirm_delete.html', {'patient': patient})


@login_required
def trash_list(request):
    patients = Patient.objects.filter(is_deleted=True).order_by('-deleted_at')
    return render(request, 'patients/trash_list.html', {'patients': patients})


@login_required
@require_POST
def restore_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk, is_deleted=True)
    patient.is_deleted = False
    patient.deleted_at = None
    patient.updated_by = request.user
    patient.save()
    messages.success(request, 'Patient restored successfully.')
    return redirect('patients:trash_list')


# --- Doctors ---

@login_required
def doctor_list(request):
    doctors = Doctor.objects.order_by('name')
    return render(request, 'patients/doctor_list.html', {'doctors': doctors})


@admin_required
def register_doctor(request):
    form = DoctorForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Doctor registered successfully.')
        return redirect('patients:doctor_list')
    return render(request, 'patients/doctor_form.html', {'form': form, 'title': 'Register Doctor'})


@admin_required
def update_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    form = DoctorForm(request.POST or None, instance=doctor)
    if form.is_valid():
        form.save()
        messages.success(request, 'Doctor updated successfully.')
        return redirect('patients:doctor_list')
    return render(request, 'patients/doctor_form.html', {'form': form, 'title': 'Update Doctor'})


# --- Appointments ---

@login_required
def appointment_list(request):
    appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-created_at')
    return render(request, 'patients/appointment_list.html', {'appointments': appointments})


@login_required
def create_appointment(request):
    form = AppointmentForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Appointment created successfully.')
        return redirect('patients:appointment_list')
    return render(request, 'patients/appointment_form.html', {'form': form, 'title': 'Create Appointment'})


@login_required
def update_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    form = AppointmentForm(request.POST or None, instance=appointment)
    if form.is_valid():
        form.save()
        messages.success(request, 'Appointment updated successfully.')
        return redirect('patients:appointment_list')
    return render(request, 'patients/appointment_form.html', {'form': form, 'title': 'Update Appointment'})


# --- Bills ---

@login_required
def bill_list(request):
    bills = Bill.objects.select_related('patient').prefetch_related('payment_set').order_by('-created_at')
    return render(request, 'patients/bill_list.html', {'bills': bills})


@login_required
def create_bill(request):
    form = BillForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Bill created successfully.')
        return redirect('patients:bill_list')
    return render(request, 'patients/bill_form.html', {'form': form, 'title': 'Create Bill'})


@login_required
def bill_detail(request, pk):
    bill = get_object_or_404(Bill.objects.select_related('patient'), pk=pk)
    payments = bill.payment_set.select_related('received_by').order_by('payment_date')
    return render(request, 'patients/bill_detail.html', {'bill': bill, 'payments': payments})


@login_required
def update_bill(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    form = BillForm(request.POST or None, instance=bill)
    if form.is_valid():
        bill = form.save()
        # Total may have changed, so Paid/Partial/Unpaid must be recalculated
        bill.update_status()
        messages.success(request, 'Bill updated successfully.')
        return redirect('patients:bill_detail', pk=bill.pk)
    return render(request, 'patients/bill_form.html', {'form': form, 'title': 'Update Bill'})


@login_required
def add_payment(request, pk):
    with transaction.atomic():
        # Lock the bill row so two simultaneous payments can't both pass the balance check
        bill = get_object_or_404(Bill.objects.select_for_update(), pk=pk)
        form = PaymentForm(request.POST or None, bill=bill)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.bill = bill
            obj.received_by = request.user
            obj.save()  # Payment.save() recalculates the bill status
            messages.success(request, 'Payment recorded successfully.')
            return redirect('patients:bill_detail', pk=bill.pk)
    return render(request, 'patients/payment_form.html', {'form': form, 'bill': bill})


@login_required
def download_invoice(request, pk):
    bill = get_object_or_404(Bill.objects.select_related('patient'), pk=pk)
    payments = list(bill.payment_set.order_by('payment_date'))
    currency = settings.CURRENCY_SYMBOL

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{bill.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    left, amount_x, bottom_margin = 50, 400, 60
    line_height = 20

    def new_page_if_needed(y, needed=line_height):
        if y - needed < bottom_margin:
            p.showPage()
            p.setFont('Helvetica', 11)
            return height - 60
        return y

    # Header
    p.setFont('Helvetica-Bold', 24)
    p.drawString(left, height - 60, settings.HOSPITAL_NAME)
    p.setFont('Helvetica', 12)
    p.drawString(left, height - 80, 'Hospital Management System')

    # Line
    p.line(left, height - 90, width - left, height - 90)

    # Invoice details
    p.setFont('Helvetica-Bold', 14)
    p.drawString(left, height - 120, f'Invoice #{bill.id}')
    p.setFont('Helvetica', 12)
    p.drawString(left, height - 145, f'Patient: {bill.patient.name}')
    p.drawString(left, height - 165, f'Date: {timezone.localtime(bill.created_at).strftime("%d %b %Y")}')
    p.drawString(left, height - 185, f'Status: {bill.status}')

    # Line
    p.line(left, height - 200, width - left, height - 200)

    # Bill details
    p.setFont('Helvetica-Bold', 12)
    p.drawString(left, height - 225, 'Description')
    p.drawString(amount_x, height - 225, 'Amount')
    p.line(left, height - 235, width - left, height - 235)

    p.setFont('Helvetica', 12)
    y = height - 255
    p.drawString(amount_x, y, f'{currency} {bill.total_amount}')
    # Wrap long descriptions so they don't run into the amount column / off the page
    description = bill.description or 'Medical Services'
    for paragraph in description.splitlines() or ['']:
        for text_line in simpleSplit(paragraph, 'Helvetica', 12, amount_x - left - 20) or ['']:
            y = new_page_if_needed(y)
            p.drawString(left, y, text_line)
            y -= line_height

    # Payments
    y = new_page_if_needed(y - 25, 2 * line_height)
    p.setFont('Helvetica-Bold', 12)
    p.drawString(left, y, 'Payments Received:')
    y -= line_height
    p.setFont('Helvetica', 11)
    if not payments:
        p.drawString(left, y, '- None')
        y -= line_height
    for payment in payments:
        y = new_page_if_needed(y)
        payment_date = timezone.localtime(payment.payment_date).strftime("%d %b %Y")
        p.drawString(left, y, f'- {payment_date} | {payment.payment_method}')
        p.drawString(amount_x, y, f'{currency} {payment.amount}')
        y -= line_height

    # Totals
    y = new_page_if_needed(y, 80)
    amount_paid = sum((pay.amount for pay in payments), Decimal('0.00'))
    p.line(left, y - 10, width - left, y - 10)
    p.setFont('Helvetica-Bold', 12)
    p.drawString(left, y - 30, 'Total Amount:')
    p.drawString(amount_x, y - 30, f'{currency} {bill.total_amount}')
    p.drawString(left, y - 50, 'Amount Paid:')
    p.drawString(amount_x, y - 50, f'{currency} {amount_paid}')
    p.drawString(left, y - 70, 'Balance:')
    p.drawString(amount_x, y - 70, f'{currency} {bill.total_amount - amount_paid}')

    p.showPage()
    p.save()
    return response
