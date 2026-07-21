from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

import re
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'e.g. alex@example.com'})
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError("A user with this email address already exists. Please log in or use a different email.")
        return email
    
    COUNTRY_CHOICES = [
        ('India', 'India (₹)'),
        ('United States', 'United States ($)'),
        ('United Kingdom', 'United Kingdom (£)'),
        ('Europe', 'Europe (€)'),
        ('UAE', 'United Arab Emirates (AED)'),
    ]
    country = forms.ChoiceField(choices=COUNTRY_CHOICES, required=True, initial='India')

    mobile_no = forms.CharField(
        max_length=10,
        min_length=10,
        required=True,
        validators=[RegexValidator(r'^\d{10}$', 'Mobile number must be exactly 10 digits.')],
        widget=forms.TextInput(attrs={'placeholder': '10-digit mobile number'})
    )

    def clean_mobile_no(self):
        mobile = self.cleaned_data.get('mobile_no')
        if UserProfile.objects.filter(mobile_no__contains=mobile).exists():
            raise ValidationError("A user with this mobile number already exists.")
        return mobile
    
    address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Full delivery address'}),
        required=True
    )
    
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. New York'})
    )
    
    pincode = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        validators=[RegexValidator(r'^\d{6}$', 'Pincode must be exactly 6 digits.')],
        widget=forms.TextInput(attrs={'placeholder': '6-digit pincode'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'mobile_no', 'address', 'city', 'pincode', 'country')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add placeholders to existing UserCreationForm fields
        self.fields['username'].widget.attrs.update({'placeholder': 'Enter username'})
        self.fields['password1'].widget.attrs.update({'placeholder': '••••••••'})
        self.fields['password2'].widget.attrs.update({'placeholder': '••••••••'})

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            if not re.search(r'[A-Za-z]', password):
                raise ValidationError("Password must contain at least one letter.")
            if not re.search(r'\d', password):
                raise ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError("Password must contain at least one special character.")
        return password

    def save(self, commit=True, full_mobile=None):
        user = super().save(commit=commit)
        if commit:
            # If full_mobile is provided (from the flag picker), use it
            mobile = full_mobile if full_mobile else self.cleaned_data['mobile_no']
            UserProfile.objects.create(
                user=user,
                mobile_no=mobile,
                address=self.cleaned_data['address'],
                city=self.cleaned_data['city'],
                pincode=self.cleaned_data['pincode'],
                country=self.cleaned_data['country']
            )
        return user

class UserProfileForm(forms.ModelForm):
    COUNTRY_CHOICES = [
        ('India', 'India (₹)'),
        ('United States', 'United States ($)'),
        ('United Kingdom', 'United Kingdom (£)'),
        ('Europe', 'Europe (€)'),
        ('UAE', 'United Arab Emirates (AED)'),
    ]
    country = forms.ChoiceField(choices=COUNTRY_CHOICES, required=True)
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'e.g. alex@example.com'}))
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            user = getattr(self.instance, 'user', None)
            queryset = User.objects.filter(email__iexact=email)
            if user:
                queryset = queryset.exclude(pk=user.pk)
            if queryset.exists():
                raise ValidationError("A user with this email address already exists. Please use a different email.")
        return email
        
    class Meta:
        model = UserProfile
        fields = ('email', 'mobile_no', 'address', 'city', 'pincode', 'country')
        widgets = {
            'mobile_no': forms.TextInput(attrs={'placeholder': '10-digit mobile number'}),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Full delivery address'}),
            'city': forms.TextInput(attrs={'placeholder': 'e.g. New York'}),
            'pincode': forms.TextInput(attrs={'placeholder': '6-digit pincode'}),
        }
