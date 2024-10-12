from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter email address',   # Add placeholder for the email field
            'class': 'input-field'  # Add custom class for styling
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Your Name',  # Add placeholder for the username field
            'class': 'input-field'  # Add custom class for styling
        })
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create Password',  # Add placeholder for the password field
            'class': 'input-field'  # Add custom class for styling
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm Password',  # Add placeholder for the confirm password field
            'class': 'input-field'  # Add custom class for styling
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': 'Enter email address',
        'class': 'input-field'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Password',
        'class': 'input-field'
    }))





