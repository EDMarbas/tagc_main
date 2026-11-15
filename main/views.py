from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from members.models import StaffNotification


def home(request):
    return render(request, "main/home.html")


@sensitive_post_parameters("password1", "password2")
@never_cache
@require_http_methods(["GET", "POST", "HEAD"])
def register(request):
    if request.user.is_authenticated:
        return redirect("members:my_membership")

    form = UserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                StaffNotification.objects.create(
                    kind=StaffNotification.Kind.REGISTRATION, subject=user.get_username(),
                )
        except IntegrityError:
            if not get_user_model().objects.filter(username=form.cleaned_data["username"]).exists():
                raise
            form.add_error("username", form.instance.unique_error_message(form._meta.model, ("username",)))
        else:
            login(request, user)
            return redirect("members:my_membership")

    return render(request, "registration/register.html", {"form": form})
