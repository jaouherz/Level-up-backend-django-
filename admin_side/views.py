from datetime import datetime  # This imports the datetime class from datetime module
from django.shortcuts import render

def admin_dashboard(request):
    context = {
        'current_date': datetime.now().strftime('%B %d, %Y')
    }
    return render(request, "admin_panel/dashboard.html", context)


def users(request):
       
    return render(request, "admin_panel/users.html")

def offers(request):
       
    return render(request, "admin_panel/offers.html")
def companies(request):
       
    return render(request, "admin_panel/companies.html")
def universities(request):
       
    return render(request, "admin_panel/universities.html")