from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()

    def otp_expired(self):
        if not self.otp_created_at:
            return True
        return (timezone.now() - self.otp_created_at).seconds > 300  # 5 minutes
