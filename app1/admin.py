from django.contrib import admin
from .models import Product, RentalOrder, RepairTicket, PickupRequest

# Register your models here.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price_per_month', 'stock', 'available')
    list_filter = ('category', 'available')
    search_fields = ('name', 'description', 'material', 'color')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'image')
        }),
        ('Pricing & Inventory', {
            'fields': ('price_per_month', 'stock', 'available')
        }),
        ('Specifications', {
            'fields': ('material', 'color', 'available_durations')
        }),
    )

@admin.register(RentalOrder)
class RentalOrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rental_duration_months', 'status', 'renewal_date')
    list_filter = ('status', 'rental_duration_months')
    search_fields = ('user__username', 'product__name')
    date_hierarchy = 'created_at'

@admin.register(RepairTicket)
class RepairTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'product__name', 'description')

@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'rental', 'pickup_date', 'status')
    list_filter = ('status', 'pickup_date')
    search_fields = ('rental__user__username', 'rental__product__name')
