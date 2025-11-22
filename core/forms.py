"""Forms for the core app."""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import MushroomImage, UnknownMushroom

class MushroomImageForm(forms.ModelForm):
    """Form for uploading and analyzing mushroom images."""
    
    class Meta:
        model = MushroomImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'})
        } 

class UnknownMushroomForm(forms.ModelForm):
    """Form to report mushrooms not in dataset."""
    latitude = forms.DecimalField(
        max_digits=9, 
        decimal_places=6,
        required=True,
        widget=forms.NumberInput(attrs={
            'step': '0.000001', 
            'class': 'form-control',
            'id': 'id_latitude',
            'name': 'latitude'
        })
    )
    longitude = forms.DecimalField(
        max_digits=9, 
        decimal_places=6,
        required=True,
        widget=forms.NumberInput(attrs={
            'step': '0.000001', 
            'class': 'form-control',
            'id': 'id_longitude',
            'name': 'longitude'
        })
    )
    
    class Meta:
        model = UnknownMushroom
        fields = ['name', 'description', 'scientific_name', 'origin', 'image', 'latitude', 'longitude']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Species name (e.g., Agaricus bisporus)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Additional description, notes, or characteristics...', 'rows': 3}),
            'scientific_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scientific name (if known)'}),
            'origin': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Origin / habitat notes (optional)', 'rows': 3}),
            'image': forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'}),
        }


class UnknownMushroomAdminForm(forms.ModelForm):
    """Admin form to add/edit reported mushrooms with status and pin color."""
    pin_color = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = UnknownMushroom
        fields = ['name', 'description', 'scientific_name', 'origin', 'image', 'latitude', 'longitude', 'status', 'pin_color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Species name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Reporter description or notes', 'rows': 3}),
            'scientific_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scientific name (for admin use)'}),
            'origin': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Origin / habitat notes (for admin use)', 'rows': 3}),
            'image': forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001', 'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class UserRegistrationForm(UserCreationForm):
    """Registration form with username, email, and password fields."""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email