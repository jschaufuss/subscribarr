from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User

# Local registration disabled: creation form removed

class CustomUserChangeForm(UserChangeForm):
    password = None  # Password change via separate form
    
    class Meta:
        model = User
        fields = ('email', 'notification_channel', 'ntfy_topic', 'apprise_url')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'text-input', 'placeholder': 'Email address'}),
            'ntfy_topic': forms.TextInput(attrs={'class': 'text-input', 'placeholder': 'ntfy topic (optional)'}),
            'apprise_url': forms.Textarea(attrs={'rows': 2, 'placeholder': 'apprise://... or other URL'}),
        }

class JellyfinLoginForm(forms.Form):
    username = forms.CharField(label='Username', widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
