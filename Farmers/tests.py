from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail

from .models import Farmer, UserProfile
from .forms import FarmerCreateByAgentForm


class FarmerEmailUniquenessTests(TestCase):
    """Tests for unique email constraint on the Farmer model."""

    def test_create_farmer_with_unique_email(self):
        farmer = Farmer.objects.create_user(username="farmer1", email="a@example.com", password="pass")
        self.assertEqual(farmer.email, "a@example.com")

    def test_duplicate_email_raises_error_at_model_level(self):
        Farmer.objects.create_user(username="farmer1", email="dup@example.com", password="pass")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Farmer.objects.create_user(username="farmer2", email="dup@example.com", password="pass")

    def test_email_field_is_unique(self):
        email_field = Farmer._meta.get_field("email")
        self.assertTrue(email_field.unique)


class FarmerCreateByAgentFormTests(TestCase):
    """Tests for FarmerCreateByAgentForm validation."""

    def setUp(self):
        self.existing_farmer = Farmer.objects.create_user(
            username="existing", email="existing@example.com", password="pass"
        )

    def test_valid_form(self):
        form = FarmerCreateByAgentForm(data={"username": "newfarmer", "email": "new@example.com"})
        self.assertTrue(form.is_valid())

    def test_duplicate_email_rejected(self):
        form = FarmerCreateByAgentForm(data={"username": "newfarmer", "email": "existing@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("already exists", form.errors["email"][0])

    def test_duplicate_email_case_insensitive(self):
        form = FarmerCreateByAgentForm(data={"username": "newfarmer", "email": "EXISTING@EXAMPLE.COM"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_invalid_email_format_rejected(self):
        form = FarmerCreateByAgentForm(data={"username": "newfarmer", "email": "not-an-email"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_duplicate_username_rejected(self):
        form = FarmerCreateByAgentForm(data={"username": "existing", "email": "other@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_missing_email_rejected(self):
        form = FarmerCreateByAgentForm(data={"username": "newfarmer", "email": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class CreateFarmerViewTests(TestCase):
    """Tests for the create_farmer view used by field agents."""

    def setUp(self):
        self.client = Client()
        self.agent = Farmer.objects.create_user(
            username="agent1", email="agent@example.com", password="agentpass"
        )
        self.agent_profile = self.agent.profile
        self.agent_profile.role = "field_agent"
        self.agent_profile.is_approved = True
        self.agent_profile.save()

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse("create_farmer"))
        self.assertRedirects(response, "/login/?next=/api/farmers/agent/create-farmer/")

    def test_non_agent_gets_forbidden(self):
        farmer = Farmer.objects.create_user(
            username="regularfarmer", email="reg@example.com", password="pass"
        )
        farmer.profile.role = "farmer"
        farmer.profile.is_approved = True
        farmer.profile.save()
        self.client.force_login(farmer)
        response = self.client.get(reverse("create_farmer"))
        self.assertEqual(response.status_code, 403)

    def test_agent_can_get_create_form(self):
        self.client.force_login(self.agent)
        response = self.client.get(reverse("create_farmer"))
        self.assertEqual(response.status_code, 200)

    def test_agent_can_create_farmer(self):
        self.client.force_login(self.agent)
        response = self.client.post(reverse("create_farmer"), {
            "username": "newfarmer",
            "email": "newfarmer@example.com",
        })
        self.assertRedirects(response, reverse("agent_dashboard"))
        farmer = Farmer.objects.get(username="newfarmer")
        self.assertEqual(farmer.email, "newfarmer@example.com")
        self.assertFalse(farmer.has_usable_password())
        self.assertFalse(farmer.profile.is_approved)
        self.assertEqual(farmer.profile.role, "farmer")

    def test_duplicate_email_shows_error(self):
        Farmer.objects.create_user(username="existing", email="taken@example.com", password="pass")
        self.client.force_login(self.agent)
        response = self.client.post(reverse("create_farmer"), {
            "username": "anotherfarmer",
            "email": "taken@example.com",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")


class AdminApprovalEmailTests(TestCase):
    """Tests that admin approval sends a password setup email."""

    def setUp(self):
        self.client = Client()
        self.superuser = Farmer.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        # Superuser must be approved to pass the login signal check
        self.superuser.profile.is_approved = True
        self.superuser.profile.save()
        self.farmer = Farmer.objects.create_user(
            username="pendingfarmer", email="farmer@example.com", password="x"
        )
        self.farmer.profile.role = "farmer"
        self.farmer.profile.is_approved = False
        self.farmer.profile.save()

    def test_approve_action_sets_is_approved(self):
        from django.test import override_settings
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.client.force_login(self.superuser)
            profile_id = self.farmer.profile.pk
            self.client.post(
                reverse("admin:Farmers_userprofile_changelist"),
                {
                    "action": "approve_farmers",
                    "_selected_action": [profile_id],
                },
            )
        self.farmer.profile.refresh_from_db()
        self.assertTrue(self.farmer.profile.is_approved)

    def test_approve_action_sends_email(self):
        from django.test import override_settings
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.client.force_login(self.superuser)
            profile_id = self.farmer.profile.pk
            self.client.post(
                reverse("admin:Farmers_userprofile_changelist"),
                {
                    "action": "approve_farmers",
                    "_selected_action": [profile_id],
                },
            )
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn("farmer@example.com", mail.outbox[0].to)
            self.assertIn("approved", mail.outbox[0].subject.lower())

