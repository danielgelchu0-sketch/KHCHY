from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import MemberProfile


class RegistrationForm(UserCreationForm):
    full_name_en = forms.CharField(max_length=255, label="Full Name (English)")
    full_name_am = forms.CharField(max_length=255, required=False, label="Full Name (Amharic)")
    phone_number = forms.CharField(max_length=20, required=False)
    voice_part = forms.ChoiceField(choices=MemberProfile.VOICE_CHOICES, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            MemberProfile.objects.create(
                user=user,
                full_name_en=self.cleaned_data['full_name_en'],
                full_name_am=self.cleaned_data.get('full_name_am', ''),
                phone_number=self.cleaned_data.get('phone_number', ''),
                voice_part=self.cleaned_data.get('voice_part', ''),
                status='pending',
            )
        return user