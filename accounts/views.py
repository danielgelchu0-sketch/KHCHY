from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render

from .forms import LoginForm, RegistrationForm


def get_is_amharic(request):
    lang = request.GET.get('lang')
    if not lang and hasattr(request, 'session'):
        lang = request.session.get('django_language')
    if not lang:
        lang = request.COOKIES.get('django_language')
    return lang == 'am'


class CustomLoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_amharic'] = get_is_amharic(self.request)
        return kwargs


def register(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    is_amharic = get_is_amharic(request)

    if request.method == 'POST':
        form = RegistrationForm(request.POST, is_amharic=is_amharic)
        if form.is_valid():
            user = form.save()
            login(request, user)
            msg = (
                "ምዝገባው በተሳካ ሁኔታ ተጠናቋል። መለያዎ በአስተዳዳሪው እውቅና እስኪያገኝ ድረስ በመጠባበቅ ላይ ነው።"
                if is_amharic
                else "Registration successful. Your account is pending admin approval."
            )
            messages.success(request, msg)
            return redirect('core:home')
    else:
        form = RegistrationForm(is_amharic=is_amharic)

    return render(request, 'accounts/register.html', {'form': form})