from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class CustomUserChangeForm(UserChangeForm):
    password = None  # Passwort-Änderung über extra Formular
    
    class Meta:
        model = User
        fields = ('email',)
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'text-input', 'placeholder': 'E-Mail-Adresse'}),
        }

class JellyfinLoginForm(forms.Form):
    username = forms.CharField(label='Benutzername', widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Passwort', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
