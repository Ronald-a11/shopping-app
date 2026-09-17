from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import ContactMessage, MessageReply, Order, Product, UserProfile, DeliveryBooking


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'phone_number', 'gender', 'age_group', 'message_type', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Your Name'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': '+263 XX XXX XXXX'
            }),
            'gender': forms.Select(attrs={
                'class': 'input'
            }),
            'age_group': forms.Select(attrs={
                'class': 'input'
            }),
            'message_type': forms.Select(attrs={
                'class': 'input'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Subject'
            }),
            'message': forms.Textarea(attrs={
                'class': 'input',
                'rows': 5,
                'placeholder': 'Your message or complaint...'
            }),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['delivery_address', 'delivery_city', 'delivery_phone']
        widgets = {
            'delivery_address': forms.Textarea(attrs={
                'class': 'input',
                'rows': 3,
                'placeholder': 'Enter your full address'
            }),
            'delivery_city': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Enter your city or town'
            }),
            'delivery_phone': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': '+263 XX XXX XXXX'
            }),
        }


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'input'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address', 'city', 'province', 'postal_code', 'date_of_birth']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': '+263 XX XXX XXXX'
            }),
            'address': forms.Textarea(attrs={
                'class': 'input',
                'rows': 3,
                'placeholder': 'Enter your full address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Enter your city or town'
            }),
            'province': forms.Select(attrs={
                'class': 'input'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Postal Code'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'input',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Zimbabwe provinces
        PROVINCE_CHOICES = [
            ('', 'Select Province'),
            ('Harare', 'Harare'),
            ('Bulawayo', 'Bulawayo'),
            ('Manicaland', 'Manicaland'),
            ('Mashonaland Central', 'Mashonaland Central'),
            ('Mashonaland East', 'Mashonaland East'),
            ('Mashonaland West', 'Mashonaland West'),
            ('Masvingo', 'Masvingo'),
            ('Matabeleland North', 'Matabeleland North'),
            ('Matabeleland South', 'Matabeleland South'),
            ('Midlands', 'Midlands'),
        ]
        self.fields['province'].choices = PROVINCE_CHOICES


class DeliveryBookingForm(forms.ModelForm):
    class Meta:
        model = DeliveryBooking
        fields = ['delivery_date', 'time_slot', 'delivery_address', 'delivery_city', 'delivery_phone', 'special_instructions']
        widgets = {
            'delivery_date': forms.DateInput(attrs={
                'class': 'input',
                'type': 'date'
            }),
            'time_slot': forms.Select(attrs={
                'class': 'input'
            }),
            'delivery_address': forms.Textarea(attrs={
                'class': 'input',
                'rows': 3,
                'placeholder': 'Enter delivery address'
            }),
            'delivery_city': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Enter your city or town'
            }),
            'delivery_phone': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': '+263 XX XXX XXXX'
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'input',
                'rows': 3,
                'placeholder': 'Any special delivery instructions (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_city'].required = True
        # Stop the date picker offering days that are already gone.
        self.fields['delivery_date'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data['delivery_date']
        if delivery_date < timezone.localdate():
            raise forms.ValidationError("Delivery date cannot be in the past.")
        return delivery_date


class DeliveryCancellationForm(forms.Form):
    cancellation_reason = forms.ChoiceField(
        choices=DeliveryBooking.CANCELLATION_REASONS,
        widget=forms.Select(attrs={
            'class': 'input'
        })
    )
    cancellation_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'input',
            'rows': 3,
            'placeholder': 'Additional notes (optional)'
        })
    )


class MessageReplyForm(forms.ModelForm):
    """A reply in the conversation about a contact message."""

    class Meta:
        model = MessageReply
        fields = ['body']
        labels = {'body': 'Your reply'}
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'input',
                'rows': 4,
                'placeholder': 'Write your reply…'
            }),
        }

    def clean_body(self):
        body = self.cleaned_data['body'].strip()
        if not body:
            raise forms.ValidationError('Please write a reply before sending.')
        return body


class StaffReplyForm(MessageReplyForm):
    mark_resolved = forms.BooleanField(required=False, label='Mark as resolved')


# Staff dashboard ---------------------------------------------------------------

# Far more than the shop will ever hold of one product. The cap keeps a slip
# such as a barcode scanned into the quantity box from overflowing the column.
MAX_STOCK_QUANTITY = 1_000_000

CHECKBOX_CLASS = 'size-4 accent-brand-600'


class ProductForm(forms.ModelForm):
    """Add or edit a product from the staff dashboard.

    Stock isn't edited here: every change to it goes through a restock or a
    correction so that it is logged. A new product can start with an opening
    stock, which is logged as its first restock.
    """
    opening_stock = forms.IntegerField(
        required=False, min_value=0, max_value=MAX_STOCK_QUANTITY, initial=0,
        label='Opening stock',
        help_text='How many you have on the shelf right now. You can add more later with a restock.',
        widget=forms.NumberInput(attrs={'class': 'input', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'image', 'supplier',
                  'is_local_product', 'is_available']
        labels = {
            'price': 'Price (USD)',
            'image': 'Picture',
            'is_local_product': 'Local product',
            'is_available': 'Show in the shop',
        }
        help_texts = {
            'image': 'A web address or /static/ path. Leave blank to use a placeholder picture.',
            'is_available': 'Untick to hide the product from customers without deleting it.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Product name'}),
            'description': forms.Textarea(attrs={
                'class': 'input',
                'rows': 3,
                'placeholder': 'What customers should know about it'
            }),
            'category': forms.Select(attrs={'class': 'input'}),
            'price': forms.NumberInput(attrs={'class': 'input', 'min': 0, 'step': '0.01', 'inputmode': 'decimal'}),
            'image': forms.TextInput(attrs={'class': 'input', 'placeholder': '/static/images/products/…'}),
            'supplier': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Who you buy it from'}),
            'is_local_product': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
            'is_available': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = 'Choose a category'
        if self.instance.pk:
            # Only a new product has an opening stock.
            del self.fields['opening_stock']


class RestockForm(forms.Form):
    """Stock received from a supplier."""
    quantity = forms.IntegerField(
        min_value=1, max_value=MAX_STOCK_QUANTITY, label='Units received',
        widget=forms.NumberInput(attrs={'class': 'input', 'min': 1, 'step': 1, 'inputmode': 'numeric'}),
    )
    unit_cost = forms.DecimalField(
        required=False, min_value=0, max_digits=10, decimal_places=2, label='Cost per unit (USD)',
        help_text="What you paid for each one. Without it the units are still counted, but not their cost.",
        widget=forms.NumberInput(attrs={'class': 'input', 'min': 0, 'step': '0.01', 'inputmode': 'decimal'}),
    )
    supplier = forms.CharField(
        required=False, max_length=200,
        help_text="Leave blank to use the product's usual supplier.",
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Supplier'}),
    )
    note = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Invoice number or other note (optional)'}),
    )


class StockAdjustForm(forms.Form):
    """A corrected stock count, for breakage, theft or a miscount."""
    new_quantity = forms.IntegerField(
        min_value=0, max_value=MAX_STOCK_QUANTITY, label='Counted stock',
        widget=forms.NumberInput(attrs={'class': 'input', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
    )
    note = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Reason, e.g. damaged in storage (optional)'}),
    )
