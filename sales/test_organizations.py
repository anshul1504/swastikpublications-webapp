from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import CompanyProfile, Customer, Invoice


class OrganizationManagementTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("admin", password="test-pass", is_staff=True)
        self.user = User.objects.create_user("sales", password="test-pass")

    def test_management_requires_staff_access(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sales:organization_list"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_create_and_change_default(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("sales:organization_add"),
            {
                "name": "Swastik Publications",
                "legal_name": "Swastik Publications Pvt Ltd",
                "gstin": "09abcde1234f1z5",
                "state_code": "09",
                "invoice_prefix": "sp",
                "is_active": "on",
                "is_default": "on",
            },
        )
        self.assertRedirects(response, reverse("sales:organization_list"))
        organization = CompanyProfile.objects.get()
        self.assertTrue(organization.is_default)
        self.assertEqual(organization.gstin, "09ABCDE1234F1Z5")
        self.assertEqual(organization.invoice_prefix, "SP")

        second = CompanyProfile.objects.create(name="Second")
        self.client.post(reverse("sales:organization_set_default", args=[second.pk]))
        organization.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(organization.is_default)
        self.assertTrue(second.is_default)
        self.assertTrue(second.is_active)

    def test_linked_organization_cannot_be_deleted(self):
        organization = CompanyProfile.objects.create(name="Linked")
        customer = Customer.objects.create(name="Customer")
        Invoice.objects.create(
            number="INV-ORG-1",
            date="2026-07-28",
            company=organization,
            customer=customer,
        )
        self.client.force_login(self.staff)
        self.client.post(reverse("sales:organization_delete", args=[organization.pk]))
        self.assertTrue(CompanyProfile.objects.filter(pk=organization.pk).exists())

    def test_sidebar_shows_administration_only_for_staff(self):
        organization = CompanyProfile.objects.create(name="Primary", is_default=True)
        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse("sales:organization_list"))
        self.assertContains(staff_response, "Users & Permissions")
        self.assertContains(staff_response, organization.name)

        self.client.force_login(self.user)
        user_response = self.client.get(reverse("dashboard"))
        self.assertNotContains(user_response, "Users & Permissions")
