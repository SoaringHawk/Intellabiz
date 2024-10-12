from .models import Agent
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['description']  # Add other fields as needed
        labels = {
            'description': 'Agent Description',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
