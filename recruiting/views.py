from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone

from api.models import Offer, Application
from .forms import OfferForm, ApplicationStatusForm, FeedbackForm
from .decorators import recruiter_required

@recruiter_required
def rh_dashboard(request):
    # Quick KPIs for this recruiter
    my_offers = Offer.objects.filter(created_by=request.user).annotate(app_count=Count("applications"))
    total_offers = my_offers.count()
    total_apps = sum(o.app_count for o in my_offers)
    open_offers = my_offers.filter(is_closed=False).count()

    context = {
        "total_offers": total_offers,
        "total_apps": total_apps,
        "open_offers": open_offers,
        "offers": my_offers.order_by("-created_at")[:5],  # recent 5
    }
    return render(request, "recruiting/dashboard.html", context)

@recruiter_required
def offer_list(request):
    offers = Offer.objects.filter(created_by=request.user).order_by("-created_at")
    return render(request, "recruiting/offer_list.html", {"offers": offers})

@recruiter_required
def offer_create(request):
    if request.method == "POST":
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.created_by = request.user
            offer.save()
            form.save_m2m()
            messages.success(request, "Offer created.")
            return redirect("recruiting:offer_list")
    else:
        form = OfferForm()
    return render(request, "recruiting/offer_form.html", {"form": form, "title": "New Offer"})

@recruiter_required
def offer_edit(request, pk):
    offer = get_object_or_404(Offer, pk=pk, created_by=request.user)
    if request.method == "POST":
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, "Offer updated.")
            return redirect("recruiting:offer_list")
    else:
        form = OfferForm(instance=offer)
    return render(request, "recruiting/offer_form.html", {"form": form, "title": "Edit Offer"})

@recruiter_required
def offer_close(request, pk):
    offer = get_object_or_404(Offer, pk=pk, created_by=request.user)
    offer.is_closed = True
    offer.closed_at = timezone.now()
    offer.save(update_fields=["is_closed", "closed_at"])
    messages.info(request, "Offer closed.")
    return redirect("recruiting:offer_list")

@recruiter_required
def offer_applications(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id, created_by=request.user)
    applications = offer.applications.select_related("user").order_by("-created_at")
    status_forms = {a.id: ApplicationStatusForm(instance=a, prefix=str(a.id)) for a in applications}
    return render(request, "recruiting/offer_applications.html", {
        "offer": offer,
        "applications": applications,
        "status_forms": status_forms,
    })

@recruiter_required
def application_update_status(request, app_id):
    app = get_object_or_404(Application, pk=app_id, offer__created_by=request.user)
    form = ApplicationStatusForm(request.POST or None, instance=app)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Status updated to {app.status}.")
    return redirect("recruiting:offer_apps", offer_id=app.offer_id)

@recruiter_required
def feedback_create(request, app_id):
    app = get_object_or_404(Application, pk=app_id, offer__created_by=request.user)
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.application = app
            fb.recruiter = request.user
            fb.save()
            messages.success(request, "Feedback added.")
            return redirect("recruiting:offer_apps", offer_id=app.offer_id)
    else:
        form = FeedbackForm()
    return render(request, "recruiting/feedback_form.html", {"form": form, "application": app})
