from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

def recruiter_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not profile or profile.role != "recruiter":
            messages.error(request, "You don’t have permission to access RH pages.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped