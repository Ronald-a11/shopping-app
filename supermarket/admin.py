from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (Category, Product, Cart, CartItem, Order, OrderItem, ContactMessage, MessageReply,
                     UserProfile, DeliveryBooking, StockEntry)


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
    list_editable = ['price', 'is_available']
    # Stock moves only through the dashboard's restock and correction forms, so
    # every change lands in the stock log (StockEntry). Editing it here would
    # change the shelf figure with no record, and "Stock bought" would miss it.
    # A product added here starts at 0; its opening stock goes in as a restock.
    exclude = ['stock_quantity']
    readonly_fields = ['stock_level']
    prepopulated_fields = {'name': ('name',)}

    @admin.display(description='Stock quantity')
    def stock_level(self, product):
        """The stock figure, with the way to the only place it can be changed."""
        if product.pk is None:
            return 'Starts at 0. Once the product is saved, record its opening stock on the admin dashboard.'
        return format_html(
            '{} &middot; <a href="{}#restock">Record stock received or a correction on the admin dashboard</a>',
            product.stock_quantity, reverse('dashboard_product_edit', args=[product.pk]),
        )


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


class MessageReplyInline(admin.StackedInline):
    model = MessageReply
    extra = 0
    fields = ['from_staff', 'author', 'body', 'read_by_customer', 'created_at']
    readonly_fields = ['created_at']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'gender', 'age_group', 'message_type', 'subject', 'status', 'is_read', 'is_urgent', 'created_at']
    list_filter = ['status', 'is_read', 'is_urgent', 'message_type', 'gender', 'age_group', 'created_at']
    inlines = [MessageReplyInline]
    search_fields = ['name', 'phone_number', 'subject', 'message']
    list_editable = ['is_read', 'is_urgent']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'phone_number', 'gender', 'age_group', 'user')
        }),
        ('Message Details', {
            'fields': ('message_type', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('status', 'is_read', 'is_urgent', 'created_at')
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


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ['product', 'kind', 'quantity', 'unit_cost', 'created_by', 'created_at']
    list_filter = ['kind', 'created_at']
    search_fields = ['product__name', 'supplier', 'note']
    list_select_related = ['product', 'created_by']
    # The log records what happened to the stock. Editing the figures here
    # wouldn't move the stock itself, so only the descriptive fields are open.
    readonly_fields = ['product', 'kind', 'quantity', 'stock_after', 'created_by', 'created_at']

    def has_add_permission(self, request):
        return False
