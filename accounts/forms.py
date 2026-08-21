from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import MemberProfile


class RegistrationForm(UserCreationForm):
    full_name_en = forms.CharField(max_length=255, label="Full Name (English)")
    full_name_am = forms.CharField(max_length=255, required=False, label="Full Name (Amharic)")
    phone_number = forms.CharField(max_length=20, required=False, label="Phone Number")
    voice_part = forms.ChoiceField(choices=MemberProfile.VOICE_CHOICES, required=False, label="Voice Part")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, is_amharic=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_amharic:
            self.fields['username'].label = "የተጠቃሚ ስም (Username)"
            self.fields['username'].help_text = "ፊደላት፣ ቁጥሮች እና @/./+/-/_ ብቻ ይጠቀሙ።"
            self.fields['email'].label = "ኢሜይል (Email)"
            self.fields['full_name_en'].label = "ሙሉ ስም (በእንግሊዝኛ)"
            self.fields['full_name_am'].label = "ሙሉ ስም (በአማርኛ)"
            self.fields['phone_number'].label = "ስልክ ቁጥር"
            self.fields['voice_part'].label = "የድምፅ ክፍል"
            self.fields['voice_part'].choices = [
                ('', '---------'),
                ('soprano', 'ሶፕራኖ (Soprano)'),
                ('alto', 'አልቶ (Alto)'),
                ('tenor', 'ቴነር (Tenor)'),
                ('bass', 'ባስ (Bass)'),
            ]
            if 'password1' in self.fields:
                self.fields['password1'].label = "የይለፍ ቃል"
                self.fields['password1'].help_text = "ቢያንስ 8 ፊደላት ወይም ቁጥሮች መሆን አለበት።"
            if 'password2' in self.fields:
                self.fields['password2'].label = "የይለፍ ቃል ማረጋገጫ"
                self.fields['password2'].help_text = "የይለፍ ቃልዎን ደግመው ያስገቡ።"

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


class LoginForm(AuthenticationForm):
    def __init__(self, *args, is_amharic=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_amharic:
            self.fields['username'].label = "የተጠቃሚ ስም"
            self.fields['password'].label = "የይለፍ ቃል"