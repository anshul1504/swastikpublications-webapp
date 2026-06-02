from .models import CompanyProfile

def company_profile(request):
    try:
        cp = CompanyProfile.objects.first()
    except CompanyProfile.DoesNotExist:
        cp = None
    return {"company_profile": cp}
