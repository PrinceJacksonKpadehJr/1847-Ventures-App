from django.test import TestCase, Client
from django.urls import reverse
from .models import Farmer, UserProfile, FarmActivity


class FieldAgentPermissionTests(TestCase):
    """Tests for field agent create-farmer and create-activity endpoints."""

    def setUp(self):
        self.client = Client()

        # Create an approved field agent
        self.agent = Farmer.objects.create_user(
            username="testagent", password="TestPass123!"
        )
        agent_profile = self.agent.profile
        agent_profile.role = "field_agent"
        agent_profile.is_approved = True
        agent_profile.save()

        # Create a regular (non-agent) user
        self.other_user = Farmer.objects.create_user(
            username="regularuser", password="TestPass123!"
        )
        other_profile = self.other_user.profile
        other_profile.role = "farmer"
        other_profile.is_approved = True
        other_profile.save()

    def test_field_agent_can_access_agent_dashboard(self):
        self.client.login(username="testagent", password="TestPass123!")
        response = self.client.get(reverse("agent_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_non_field_agent_cannot_access_agent_dashboard(self):
        self.client.login(username="regularuser", password="TestPass123!")
        response = self.client.get(reverse("agent_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_field_agent_can_create_farmer(self):
        self.client.login(username="testagent", password="TestPass123!")
        response = self.client.post(reverse("create_farmer"), {
            "username": "newfarmer1",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_number": "0123456789",
            "password": "",
        })
        # Should redirect to agent_dashboard after success
        self.assertRedirects(response, reverse("agent_dashboard"))
        new_farmer = Farmer.objects.get(username="newfarmer1")
        self.assertEqual(new_farmer.profile.role, "farmer")
        self.assertFalse(new_farmer.profile.is_approved)

    def test_non_field_agent_cannot_create_farmer(self):
        self.client.login(username="regularuser", password="TestPass123!")
        response = self.client.post(reverse("create_farmer"), {
            "username": "shouldnotwork",
            "first_name": "Bad",
            "last_name": "Actor",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Farmer.objects.filter(username="shouldnotwork").exists())

    def test_farmer_created_by_agent_is_pending_approval(self):
        self.client.login(username="testagent", password="TestPass123!")
        self.client.post(reverse("create_farmer"), {
            "username": "pendingfarmer",
            "first_name": "Pending",
            "last_name": "Farmer",
            "email": "",
            "phone_number": "",
            "password": "",
        })
        farmer = Farmer.objects.get(username="pendingfarmer")
        self.assertFalse(farmer.profile.is_approved)

    def test_field_agent_can_record_farm_activity(self):
        # Create an approved farmer to link to the activity
        approved_farmer = Farmer.objects.create_user(
            username="approvedfarmer", password="TestPass123!"
        )
        fp = approved_farmer.profile
        fp.role = "farmer"
        fp.is_approved = True
        fp.save()

        self.client.login(username="testagent", password="TestPass123!")
        response = self.client.post(reverse("create_farm_activity"), {
            "farmer": approved_farmer.pk,
            "activity_type": "planting",
            "farm_location": "Nimba County",
            "farm_size": "2.5",
            "crop_type": "Cocoa",
            "date_planted": "2026-03-01",
            "harvest_date": "2026-09-01",
            "expected_yield_kg": "500",
            "seeds_planted_kg": "10",
            "date": "2026-03-01",
        })
        self.assertRedirects(response, reverse("agent_dashboard"))
        activity = FarmActivity.objects.get(farmer=approved_farmer)
        self.assertEqual(activity.created_by, self.agent)
        self.assertEqual(activity.crop_type, "Cocoa")

