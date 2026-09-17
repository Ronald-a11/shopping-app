from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    # Authentication URLs
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    
    # Main URLs
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/', views.order_history, name='order_history'),
    
    # Delivery URLs
    path('delivery/booking/', views.delivery_booking, name='delivery_booking'),
    path('delivery/bookings/', views.delivery_bookings, name='delivery_bookings'),
    path('delivery/booking/<int:booking_id>/', views.delivery_booking_detail, name='delivery_booking_detail'),
    path('delivery/cancel/<int:booking_id>/', views.cancel_delivery, name='cancel_delivery'),
    
    # Other URLs
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('gallery/', views.gallery, name='gallery'),
    path('cart-count/', views.cart_count, name='cart_count'),

    # Customer conversations about their contact messages
    path('messages/', views.my_messages, name='my_messages'),
    path('messages/<int:message_id>/reply/', views.customer_reply, name='customer_reply'),
    
    # Founder Dashboard URLs
    path('founder/', admin_views.founder_dashboard, name='founder_dashboard'),
    path('founder/inventory/', admin_views.inventory, name='dashboard_inventory'),
    path('founder/inventory/add/', admin_views.product_add, name='dashboard_product_add'),
    path('founder/inventory/history/', admin_views.stock_history, name='dashboard_stock_history'),
    path('founder/inventory/<int:product_id>/edit/', admin_views.product_edit, name='dashboard_product_edit'),
    path('founder/inventory/<int:product_id>/restock/', admin_views.restock, name='dashboard_restock'),
    path('founder/inventory/<int:product_id>/adjust/', admin_views.adjust_stock, name='dashboard_adjust_stock'),
    path('founder/inventory/<int:product_id>/toggle/', admin_views.toggle_available, name='dashboard_toggle_available'),
    path('founder/orders/', admin_views.orders, name='dashboard_orders'),
    path('founder/orders/<int:order_id>/', admin_views.order_detail, name='dashboard_order_detail'),
    path('founder/orders/<int:order_id>/status/', admin_views.order_status, name='dashboard_order_status'),
    path('founder/deliveries/', admin_views.deliveries, name='dashboard_deliveries'),
    path('founder/deliveries/<int:booking_id>/status/', admin_views.delivery_status, name='dashboard_delivery_status'),
    path('founder/messages/', admin_views.dashboard_messages, name='dashboard_messages'),
    path('founder/message/<int:message_id>/', admin_views.message_detail, name='message_detail'),
    path('founder/mark-urgent/<int:message_id>/', admin_views.mark_urgent, name='mark_urgent'),
    path('founder/mark-read/<int:message_id>/', admin_views.mark_read, name='mark_read'),
    path('founder/message/<int:message_id>/reply/', admin_views.reply_to_message, name='reply_to_message'),
    path('founder/message/<int:message_id>/resolve/', admin_views.toggle_resolved, name='toggle_resolved'),
]
