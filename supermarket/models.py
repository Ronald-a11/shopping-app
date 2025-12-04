from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.CharField(max_length=200, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Zimbabwe-specific fields
    is_local_product = models.BooleanField(default=False)
    supplier = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def price_in_zwd(self):
        """Convert price to Zimbabwe Dollars (assuming 1 USD = 361 ZWD)"""
        return self.price * 361


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart {self.session_key}"
    
    def get_total(self):
        total = 0
        for item in self.items.all():
            total += item.get_total()
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def get_total(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Delivery information
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    delivery_province = models.CharField(max_length=100, blank=True, default='')
    delivery_phone = models.CharField(max_length=20)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def get_total(self):
        return self.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"


class DeliveryBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    CANCELLATION_REASONS = [
        ('customer_request', 'Customer Request'),
        ('out_of_stock', 'Out of Stock'),
        ('delivery_area', 'Outside Delivery Area'),
        ('payment_issue', 'Payment Issue'),
        ('other', 'Other'),
    ]
    
    TIME_SLOT_CHOICES = [
        ('morning', 'Morning (8:00 AM - 12:00 PM)'),
        ('afternoon', 'Afternoon (12:00 PM - 4:00 PM)'),
        ('evening', 'Evening (4:00 PM - 8:00 PM)'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    delivery_date = models.DateField()
    time_slot = models.CharField(max_length=20, choices=TIME_SLOT_CHOICES)
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    delivery_province = models.CharField(max_length=100, blank=True, default='')
    delivery_phone = models.CharField(max_length=20)
    special_instructions = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_delivery_time = models.CharField(max_length=100, blank=True)
    whatsapp_notification_sent = models.BooleanField(default=False)
    cancellation_reason = models.CharField(max_length=50, choices=CANCELLATION_REASONS, blank=True)
    cancellation_notes = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def can_be_cancelled(self):
        """Check if delivery can be cancelled"""
        return self.status in ['pending', 'confirmed']
    
    def cancel_delivery(self, reason, notes=''):
        """Cancel the delivery"""
        self.status = 'cancelled'
        self.cancellation_reason = reason
        self.cancellation_notes = notes
        self.cancelled_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Delivery booking for {self.user.username} on {self.delivery_date}"


class ContactMessage(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    AGE_GROUP_CHOICES = [
        ('under_18', 'Under 18'),
        ('18_25', '18-25'),
        ('26_35', '26-35'),
        ('36_45', '36-45'),
        ('46_55', '46-55'),
        ('56_65', '56-65'),
        ('over_65', 'Over 65'),
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('complaint', 'Complaint'),
        ('inquiry', 'General Inquiry'),
        ('suggestion', 'Suggestion'),
        ('feedback', 'Feedback'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, default='')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='prefer_not_to_say')
    age_group = models.CharField(max_length=20, choices=AGE_GROUP_CHOICES, default='18_25')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='inquiry')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.name}: {self.subject}"
