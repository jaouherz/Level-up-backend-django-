from django.shortcuts import render, redirect
from django.contrib import messages

# ⚠️ NOTE:
# These views DO NOT use request.user, because you are authenticating with JWT
# in the frontend (localStorage tokens, Authorization: Bearer ...).
# They just render templates; all data is loaded via JS calling /api/... endpoints.

def recruiter_dashboard(request):
    """
    Main HR dashboard page.
    JS on this page will:
      - Check JWT in localStorage
      - Fetch /api/offers/?mine=1 to get offers of the recruiter's company
    """
    return render(request, "recruiting/dashboard.html")


def recruiter_offers_list(request):
    """
    Page that lists the recruiter's offers.
    Data fetched via JS from /api/offers/?mine=1
    """
    return render(request, "recruiting/offer_list.html")


def recruiter_offer_detail(request, offer_id):
    """
    Page that shows a single offer and its candidates.
    JS will:
      - GET /api/offers/<offer_id>/ to show offer info
      - GET /api/offers/<offer_id>/ranked_candidates/ to list candidates
      - POST /api/applications/<application_id>/mark_fake/ to mark fake
      - POST /api/offers/<offer_id>/replace_fakes/ to get replacements
    """
    context = {"offer_id": offer_id}
    return render(request, "recruiting/offer_detail.html", context)


def recruiter_create_offer(request):
    """
    Page with a form to create a new offer.
    The form will be handled in JS and send a POST JSON to /api/offers/
    with Authorization: Bearer <access_token>.
    """
    return render(request, "recruiting/offer_create.html")