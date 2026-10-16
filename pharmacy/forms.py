from django import forms
from django.db.models import Q
from django.utils import timezone

from patients.forms import active_patients
from patients.models import Payment
from .models import Medicine
from .services import merge_items, stock_errors


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            'name', 'generic_name', 'form', 'manufacturer', 'unit_price',
            'stock_quantity', 'reorder_level', 'expiry_date', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand name'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Paracetamol'}),
            'form': forms.Select(attrs={'class': 'form-select'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {'is_active': 'Available for sale'}


class SaleForm(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payment_method = forms.ChoiceField(
        required=False,
        choices=[('', 'Pay later (add to patient bill)')] + Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Payment',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = active_patients()


def sellable_medicines():
    today = timezone.localdate()
    return Medicine.objects.filter(is_active=True, stock_quantity__gt=0).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=today)
    )


class MedicineChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.form}) - {obj.unit_price} - {obj.stock_quantity} in stock"


class SaleItemForm(forms.Form):
    medicine = MedicineChoiceField(queryset=None, widget=forms.Select(attrs={'class': 'form-select'}))
    quantity = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['medicine'].queryset = sellable_medicines()


class BaseSaleItemFormSet(forms.BaseFormSet):
    def items(self):
        return [
            (form.cleaned_data['medicine'], form.cleaned_data['quantity'])
            for form in self.forms
            if form not in self.deleted_forms
            and form.cleaned_data.get('medicine') and form.cleaned_data.get('quantity')
        ]

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        quantities = merge_items(self.items())
        if not quantities:
            raise forms.ValidationError('Add at least one medicine.')
        medicines = Medicine.objects.in_bulk(list(quantities))
        errors = stock_errors(medicines, quantities)
        if errors:
            raise forms.ValidationError(errors)


SaleItemFormSet = forms.formset_factory(
    SaleItemForm, formset=BaseSaleItemFormSet, extra=0, min_num=1, validate_min=True, can_delete=True,
)
