from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch

from .models import Farmer, UserProfile


def make_user(username, email="", role="farmer", approved=False, usable_pw=True):
    user = Farmer(username=username, email=email)
    if usable_pw:
        user.set_password("testpass123")
    else:
        user.set_unusable_password()
    user.save()
    profile = UserProfile.objects.get(user=user)
    profile.role = role
    profile.is_approved = approved
    profile.save()
    return user


class FarmerCreateByAgentFormTest(TestCase):
    def test_valid_form(self):
        from .forms import FarmerCreateByAgentForm
        form = FarmerCreateByAgentForm(data={"username": "newfarmer", "email": "newfarmer@example.com"})
        self.assertTrue(form.is_valid())

    def test_duplicate_username_rejected(self):
        from .forms import FarmerCreateByAgentForm
        make_user("existing", email="a@b.com", role="farmer", approved=True)
        form = FarmerCreateByAgentForm(data={"username": "existing", "email": "other@b.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_duplicate_email_rejected(self):
        from .forms import FarmerCreateByAgentForm
        make_user("someone", email="taken@example.com", role="farmer", approved=True)
        form = FarmerCreateByAgentForm(data={"username": "newuser", "email": "TAKEN@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class AgentDashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.agent = make_user("agent1", email="agent@example.com", role="field_agent", approved=True)

    def test_get_dashboard_requires_login(self):
        response = self.client.get(reverse("agent_dashboard"))
        self.assertRedirects(response, f"/login/?next={reverse('agent_dashboard')}")

    def test_get_dashboard_as_agent(self):
        self.client.force_login(self.agent)
        response = self.client.get(reverse("agent_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Register a New Farmer")

    def test_non_agent_blocked(self):
        farmer = make_user("farmerx", email="fx@x.com", role="farmer", approved=True)
        self.client.force_login(farmer)
        response = self.client.get(reverse("agent_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_post_creates_farmer_with_unusable_password(self):
        self.client.force_login(self.agent)
        response = self.client.post(
            reverse("agent_dashboard"),
            {"username": "farmernew", "email": "farmernew@example.com"},
        )
        self.assertRedirects(response, reverse("agent_dashboard"))
        farmer = Farmer.objects.get(username="farmernew")
        self.assertFalse(farmer.has_usable_password())
        profile = UserProfile.objects.get(user=farmer)
        self.assertEqual(profile.role, "farmer")
        self.assertFalse(profile.is_approved)


class ApprovalSignalTest(TestCase):
    @patch("Farmers.utils.send_mail")
    def test_approval_sends_email(self, mock_send_mail):
        user = make_user("pendingfarmer", email="p@example.com", role="farmer", approved=False, usable_pw=False)
        profile = UserProfile.objects.get(user=user)
        profile.is_approved = True
        profile.save()
        mock_send_mail.assert_called_once()
        args = mock_send_mail.call_args
        self.assertIn("p@example.com", args[0][3])

    @patch("Farmers.utils.send_mail")
    def test_approval_not_sent_twice(self, mock_send_mail):
        user = make_user("pendingfarmer2", email="p2@example.com", role="farmer", approved=False, usable_pw=False)
        profile = UserProfile.objects.get(user=user)
        profile.is_approved = True
        profile.save()
        # Save again -- already approved, no new email
        profile.save()
        mock_send_mail.assert_called_once()

    @patch("Farmers.utils.send_mail")
    def test_no_email_if_already_has_password(self, mock_send_mail):
        user = make_user("haspass", email="hp@example.com", role="farmer", approved=False, usable_pw=True)
        profile = UserProfile.objects.get(user=user)
        profile.is_approved = True
        profile.save()
        mock_send_mail.assert_not_called()


class LoginBlockingTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_unapproved_farmer_cannot_login(self):
        make_user("unapproved", email="u@u.com", role="farmer", approved=False)
        response = self.client.post(reverse("login"), {"username": "unapproved", "password": "testpass123"})
        # Should not redirect to dashboard
        self.assertNotEqual(response.status_code, 302)

    def test_approved_farmer_without_password_cannot_login(self):
        user = make_user("nopassfarmer", email="np@example.com", role="farmer", approved=True, usable_pw=False)
        response = self.client.post(reverse("login"), {"username": "nopassfarmer", "password": "anything"})
        self.assertNotEqual(response.status_code, 302)

    def test_approved_farmer_with_password_can_login(self):
        make_user("readyfarmer", email="rf@example.com", role="farmer", approved=True, usable_pw=True)
        response = self.client.post(reverse("login"), {"username": "readyfarmer", "password": "testpass123"}, follow=True)
        self.assertRedirects(response, reverse("farmer_dashboard"))
