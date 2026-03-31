from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core import mail

from .models import Farmer, UserProfile


def _make_agent(username="agent1"):
    """Create an approved field-agent user."""
    agent = Farmer.objects.create_user(
        username=username, password="testpass123", email=f"{username}@example.com"
    )
    profile = agent.profile
    profile.role = "field_agent"
    profile.is_approved = True
    profile.save()
    return agent


class UniqueEmailTests(TestCase):
    """Tests for duplicate-email rejection on the create_farmer form."""

    def setUp(self):
        self.client = Client()
        self.agent = _make_agent()
        self.client.login(username="agent1", password="testpass123")

    def test_create_farmer_success(self):
        """Field agent can register a new farmer with a unique email."""
        response = self.client.post(
            reverse("create_farmer"),
            {"username": "farmer_new", "email": "unique@example.com"},
        )
        self.assertRedirects(response, reverse("agent_dashboard"))
        farmer = Farmer.objects.get(username="farmer_new")
        self.assertFalse(farmer.has_usable_password())
        profile = farmer.profile
        self.assertEqual(profile.email, "unique@example.com")
        self.assertEqual(profile.role, "farmer")
        self.assertFalse(profile.is_approved)

    def test_create_farmer_stores_email_on_farmer_model(self):
        """Creating a farmer also syncs the email to Farmer.email."""
        self.client.post(
            reverse("create_farmer"),
            {"username": "farmer_sync", "email": "sync@example.com"},
        )
        farmer = Farmer.objects.get(username="farmer_sync")
        self.assertEqual(farmer.email, "sync@example.com")

    def test_duplicate_email_rejected(self):
        """Submitting an already-registered email shows a clear error."""
        # Register first farmer
        self.client.post(
            reverse("create_farmer"),
            {"username": "farmer_first", "email": "dup@example.com"},
        )
        # Try to register second farmer with same email
        response = self.client.post(
            reverse("create_farmer"),
            {"username": "farmer_second", "email": "dup@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "This email is already registered to another farmer."
        )
        # Second farmer should NOT have been created
        self.assertFalse(Farmer.objects.filter(username="farmer_second").exists())

    def test_invalid_email_rejected(self):
        """A malformed email address is rejected with a validation error."""
        response = self.client.post(
            reverse("create_farmer"),
            {"username": "farmer_bad", "email": "not-an-email"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address.")
        self.assertFalse(Farmer.objects.filter(username="farmer_bad").exists())

    def test_empty_email_rejected(self):
        """Missing email is rejected."""
        response = self.client.post(
            reverse("create_farmer"),
            {"username": "farmer_noemail", "email": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email is required.")

    def test_duplicate_username_rejected(self):
        """Submitting an already-taken username shows an error."""
        self.client.post(
            reverse("create_farmer"),
            {"username": "taken_user", "email": "first@example.com"},
        )
        response = self.client.post(
            reverse("create_farmer"),
            {"username": "taken_user", "email": "second@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This username is already taken.")

    def test_non_agent_cannot_access_create_farmer(self):
        """A farmer user cannot access the create-farmer form."""
        farmer_user = Farmer.objects.create_user(
            username="regular_farmer", password="pass123"
        )
        profile = farmer_user.profile
        profile.role = "farmer"
        profile.is_approved = True
        profile.save()
        self.client.login(username="regular_farmer", password="pass123")
        response = self.client.get(reverse("create_farmer"))
        self.assertEqual(response.status_code, 403)

    def test_unapproved_cannot_access_create_farmer(self):
        """An unapproved user cannot access the create-farmer form (blocked at login)."""
        unapproved = Farmer.objects.create_user(
            username="unapproved_agent", password="pass123"
        )
        profile = unapproved.profile
        profile.role = "field_agent"
        profile.is_approved = False
        profile.save()
        # Login is blocked by ApprovedUserBackend; direct GET should redirect
        self.client.logout()
        self.client.login(username="unapproved_agent", password="pass123")
        response = self.client.get(reverse("create_farmer"))
        # Either redirected to login or returns 403
        self.assertIn(response.status_code, [302, 403])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="no-reply@1847ventures.com",
)
class ApprovalEmailTests(TestCase):
    """Tests for admin approval action sending password setup email."""

    def setUp(self):
        self.client = Client()
        # Create superuser to access admin
        self.admin = Farmer.objects.create_superuser(
            username="superadmin", password="adminpass", email="admin@example.com"
        )
        self.client.login(username="superadmin", password="adminpass")

    def test_approve_action_sends_email(self):
        """Admin approve action marks profile approved and sends email."""
        farmer = Farmer(username="pending_farmer", email="pending@example.com")
        farmer.set_unusable_password()
        farmer.save()
        profile = farmer.profile
        profile.role = "farmer"
        profile.email = "pending@example.com"
        profile.is_approved = False
        profile.save()

        # Simulate admin action via admin changelist POST
        response = self.client.post(
            "/admin/Farmers/userprofile/",
            {
                "action": "approve_farmers",
                "_selected_action": [profile.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        profile.refresh_from_db()
        self.assertTrue(profile.is_approved)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["pending@example.com"])
        self.assertIn("Set your 1847 Ventures password", mail.outbox[0].subject)

    def test_approve_action_uses_userprofile_email_when_farmer_email_empty(self):
        """Approval email uses UserProfile.email even when Farmer.email is blank."""
        farmer = Farmer(username="noemail_farmer")
        farmer.set_unusable_password()
        farmer.save()
        # Farmer.email is empty; only UserProfile.email is set
        profile = farmer.profile
        profile.role = "farmer"
        profile.email = "profile_only@example.com"
        profile.is_approved = False
        profile.save()

        self.client.post(
            "/admin/Farmers/userprofile/",
            {
                "action": "approve_farmers",
                "_selected_action": [profile.pk],
            },
            follow=True,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["profile_only@example.com"])

        # Email should also be synced to Farmer model
        farmer.refresh_from_db()
        self.assertEqual(farmer.email, "profile_only@example.com")

    def test_approve_action_skips_profiles_without_email(self):
        """Approval action skips (warns) profiles with no email address."""
        farmer = Farmer(username="noemail2")
        farmer.set_unusable_password()
        farmer.save()
        profile = farmer.profile
        profile.role = "farmer"
        profile.email = None
        profile.is_approved = False
        profile.save()

        self.client.post(
            "/admin/Farmers/userprofile/",
            {
                "action": "approve_farmers",
                "_selected_action": [profile.pk],
            },
            follow=True,
        )
        # No email sent, profile still not approved
        self.assertEqual(len(mail.outbox), 0)
        profile.refresh_from_db()
        self.assertFalse(profile.is_approved)

