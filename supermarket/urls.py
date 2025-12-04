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
    
    # Founder Dashboard URLs
    path('founder/', admin_views.founder_dashboard, name='founder_dashboard'),
    path('founder/message/<int:message_id>/', admin_views.message_detail, name='message_detail'),
    path('founder/mark-urgent/<int:message_id>/', admin_views.mark_urgent, name='mark_urgent'),
    path('founder/mark-read/<int:message_id>/', admin_views.mark_read, name='mark_read'),
]
