from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import ContactMessage, MessageReply, Order, UserProfile, DeliveryBooking


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
