from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


def home(request):
    return render(request, "main/home.html")


@never_cache
@require_safe
def register(request):
    if request.user.is_authenticated:
        return redirect("members:my_membership")

    return render(request, "registration/register.html")
