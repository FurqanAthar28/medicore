from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render

from patients.models import Patient, Prescription
from patients.roles import get_doctor, is_admin, pharmacist_required
from .forms import MedicineForm, SaleForm, SaleItemFormSet
from .models import Medicine, Sale
from .services import StockError, create_sale


@login_required
def medicine_list(request):
    medicines = Medicine.objects.all()
    query = request.GET.get('q', '').strip()
    if query:
        medicines = medicines.filter(Q(name__icontains=query) | Q(generic_name__icontains=query))
    if request.GET.get('low'):
        medicines = medicines.filter(stock_quantity__lte=F('reorder_level'))
    return render(request, 'pharmacy/medicine_list.html', {
        'medicines': medicines, 'query': query, 'low': bool(request.GET.get('low')),
    })


@pharmacist_required
def medicine_create(request):
    form = MedicineForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Medicine added.')
        return redirect('pharmacy:medicine_list')
    return render(request, 'pharmacy/medicine_form.html', {'form': form, 'title': 'Add Medicine'})


@pharmacist_required
def medicine_update(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    form = MedicineForm(request.POST or None, instance=medicine)
    if form.is_valid():
        form.save()
        messages.success(request, 'Medicine updated.')
        return redirect('pharmacy:medicine_list')
    return render(request, 'pharmacy/medicine_form.html', {'form': form, 'title': 'Update Medicine'})


@login_required
def sale_list(request):
    sales = Sale.objects.select_related('patient', 'sold_by', 'bill').order_by('-created_at')
    return render(request, 'pharmacy/sale_list.html', {'sales': sales})


@login_required
def sale_create(request):
    """Sell medicines to a patient, optionally dispensing a prescription."""
    prescription = None
    initial = {}
    item_initial = []
    if request.GET.get('prescription', '').isdigit():
        prescription = get_object_or_404(
            Prescription.objects.select_related('patient'), pk=request.GET['prescription'],
        )
        doctor = get_doctor(request.user)
        if doctor and not is_admin(request.user) and prescription.doctor_id != doctor.pk:
            messages.error(request, "You can only dispense your own prescriptions.")
            return redirect('patients:prescription_list')
        if prescription.is_dispensed:
            messages.warning(request, 'This prescription has already been dispensed.')
        initial['patient'] = prescription.patient_id
        item_initial = [
            {'medicine': item.medicine_id, 'quantity': item.quantity}
            for item in prescription.items.all()
        ]
    elif request.GET.get('patient', '').isdigit():
        initial['patient'] = get_object_or_404(Patient, pk=request.GET['patient'], is_deleted=False).pk

    form = SaleForm(request.POST or None, initial=initial)
    formset = SaleItemFormSet(request.POST or None, initial=item_initial or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        if prescription and form.cleaned_data['patient'].pk != prescription.patient_id:
            form.add_error('patient', 'Patient must match the prescription.')
        else:
            try:
                sale = create_sale(
                    patient=form.cleaned_data['patient'],
                    items=formset.items(),
                    user=request.user,
                    prescription=prescription,
                    payment_method=form.cleaned_data['payment_method'] or None,
                )
            except StockError as error:
                # Stock changed between form validation and the locked re-check
                for message in error.errors:
                    messages.error(request, message)
            else:
                messages.success(request, f'Sale #{sale.id} completed. Bill #{sale.bill_id} created.')
                return redirect('pharmacy:sale_detail', pk=sale.pk)
    return render(request, 'pharmacy/sale_form.html', {
        'form': form, 'formset': formset, 'prescription': prescription,
    })


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('patient', 'sold_by', 'bill', 'prescription'), pk=pk)
    return render(request, 'pharmacy/sale_detail.html', {
        'sale': sale, 'items': sale.items.select_related('medicine'),
    })
