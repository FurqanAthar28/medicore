from django.contrib import admin
from .models import Patient, Doctor, Appointment, Bill, Payment


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'gender', 'phone', 'is_deleted', 'created_at')
    list_filter = ('is_deleted', 'gender')
    search_fields = ('name', 'phone')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'phone', 'email')
    search_fields = ('name', 'specialization')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
    list_filter = ('status', 'appointment_date')


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)
    # Status is derived from payments; editing it by hand would make it inconsistent
    readonly_fields = ('status',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.update_status()


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('bill', 'amount', 'payment_method', 'received_by', 'payment_date')
    list_filter = ('payment_method',)

    def delete_queryset(self, request, queryset):
        # Bulk delete bypasses Payment.delete(), so refresh affected bill statuses manually
        bills = list(Bill.objects.filter(payment__in=queryset).distinct())
        super().delete_queryset(request, queryset)
        for bill in bills:
            bill.update_status()
