from django.contrib import admin
from .models import Category, Product, Cart, CartItem, Order, OrderItem, ContactMessage, UserProfile, DeliveryBooking


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'name': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity', 'is_available', 'is_local_product', 'created_at']
    list_filter = ['category', 'is_available', 'is_local_product', 'created_at']
    search_fields = ['name', 'description', 'supplier']
    list_editable = ['price', 'stock_quantity', 'is_available']
    prepopulated_fields = {'name': ('name',)}


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'created_at', 'get_total']
    inlines = [CartItemInline]
    
    def get_total(self, obj):
        return f"${obj.get_total():.2f}"
    get_total.short_description = 'Total'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total_amount', 'delivery_city', 'created_at']
    list_filter = ['status', 'delivery_province', 'created_at']
    search_fields = ['order_number', 'user__username', 'delivery_address']
    inlines = [OrderItemInline]
    readonly_fields = ['order_number', 'created_at', 'updated_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'get_total']
    list_filter = ['order__status']
    
    def get_total(self, obj):
        return f"${obj.get_total():.2f}"
    get_total.short_description = 'Total'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'gender', 'age_group', 'message_type', 'subject', 'is_read', 'is_urgent', 'created_at']
    list_filter = ['is_read', 'is_urgent', 'message_type', 'gender', 'age_group', 'created_at']
    search_fields = ['name', 'phone_number', 'subject', 'message']
    list_editable = ['is_read', 'is_urgent']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'phone_number', 'gender', 'age_group')
        }),
        ('Message Details', {
            'fields': ('message_type', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'is_urgent', 'created_at')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'city', 'province', 'created_at']
    list_filter = ['province', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone_number', 'city']


@admin.register(DeliveryBooking)
class DeliveryBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'delivery_date', 'time_slot', 'delivery_city', 'status', 'delivery_fee', 'estimated_delivery_time', 'cancellation_reason', 'created_at']
    list_filter = ['status', 'delivery_city', 'time_slot', 'cancellation_reason', 'created_at']
    search_fields = ['user__username', 'delivery_address', 'delivery_city', 'delivery_phone']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at', 'cancelled_at']
    
    fieldsets = (
        ('Delivery Information', {
            'fields': ('user', 'order', 'delivery_date', 'time_slot', 'delivery_address', 'delivery_city', 'delivery_phone', 'special_instructions')
        }),
        ('Status & Fees', {
            'fields': ('status', 'delivery_fee', 'estimated_delivery_time', 'whatsapp_notification_sent')
        }),
        ('Cancellation', {
            'fields': ('cancellation_reason', 'cancellation_notes', 'cancelled_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
