from .models import CompanyProfile

def company_profile(request):
    try:
        cp = CompanyProfile.objects.order_by("-is_default", "-is_active", "pk").first()
    except CompanyProfile.DoesNotExist:
        cp = None
    return {"company_profile": cp}
