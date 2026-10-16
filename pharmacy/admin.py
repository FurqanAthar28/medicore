from django.contrib import admin
from .models import Medicine, Sale, SaleItem


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'form', 'unit_price', 'stock_quantity', 'expiry_date', 'is_active')
    list_filter = ('form', 'is_active')
    search_fields = ('name', 'generic_name')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('medicine', 'quantity', 'unit_price')
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    # Sales adjust stock and billing, so they are read-only here; create them from the pharmacy screen
    list_display = ('id', 'patient', 'total_amount', 'sold_by', 'created_at')
    readonly_fields = ('patient', 'prescription', 'bill', 'total_amount', 'sold_by')
    inlines = [SaleItemInline]

    def has_add_permission(self, request):
        return False
