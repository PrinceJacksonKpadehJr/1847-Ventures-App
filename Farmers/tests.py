import tempfile
import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.db import IntegrityError

from .models import (
    Farmer,
    UserProfile,
    AdminNotification,
    PasswordResetRequest,
    Farm,
    FarmActivity,
    Harvest,
    Investment,
    Message,
    Notification,
    FarmAssessmentSheet1,
    FarmAssessmentSheet2,
    FarmAssessmentSheet3,
    InvestorDatasetImport,
    InvestorDatasetRow,
    DatasetAuditLog,
)
from .forms import (
    FarmerCreateByAgentForm,
    FarmAssessmentSheet1Form,
    FarmAssessmentSheet2Form,
    FarmAssessmentSheet3Form,
)


TEST_IMAGE_BYTES = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
    b"\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00"
    b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01"
    b"\x00\x3b"
)


def make_test_image(name):
    return SimpleUploadedFile(name, TEST_IMAGE_BYTES, content_type="image/gif")


def make_agent_farmer_form_data(**overrides):
    data = {
        "username": "newfarmer",
        "email": "new@example.com",
        "full_name": "Kojo Mensah",
        "household_size": "3-5",
        "belongs_to_group": "no",
        "farmer_group_name": "",
        "latitude": "5.603717",
        "longitude": "-0.186964",
        "location_name": "Accra",
        "location_confirmed": "yes",
        "land_ownership": "own",
        "farm_size_category": "small",
        "has_shade_trees": "none",
        "shade_tree_types": "",
        "uses_fertilizer": "no",
        "fertilizer_bag_range": "none",
        "fertilizer_application": "",
        "burns_farm_waste": "never",
        "received_training": "yes",
        "plants_trees": "yes",
        "practices_agroforestry": "no",
        "harvest_y1_bags": "0-5",
        "harvest_y2_bags": "",
        "harvest_y3_bags": "",
    }
    data.update(overrides)
    return data


def make_agent_farmer_form_files(**overrides):
    files = {
        "photo_of_farmer": make_test_image("farmer.gif"),
        "photo_of_farm": make_test_image("farm.gif"),
    }
    files.update(overrides)
    return files


def make_agent_farmer_form_payload(**overrides):
    data_overrides = {key: value for key, value in overrides.items() if key not in {"photo_of_farmer", "photo_of_farm"}}
    file_overrides = {key: value for key, value in overrides.items() if key in {"photo_of_farmer", "photo_of_farm"}}
    payload = make_agent_farmer_form_data(**data_overrides)
    payload.update(make_agent_farmer_form_files(**file_overrides))
    return payload


def make_test_csv(name="portfolio.csv"):
    csv_content = (
        "farmer_name,yield_kg,harvest_date,is_active\n"
        "Ama,1200,2024-01-12,yes\n"
        "Kojo,\"$1,200\",12/01/2024,no\n"
        "Ama,1200,2024-01-12,yes\n"
        "Esi,,2024/02/14,TRUE\n"
    )
    return SimpleUploadedFile(name, csv_content.encode("utf-8"), content_type="text/csv")


def make_noisy_type_csv(name="noisy_types.csv"):
    csv_content = (
        "region,amount,report_date\n"
        "North,100,2024-01-01\n"
        "South,200,2024/01/02\n"
        "West,,03/01/2024\n"
        "East,bad,2024-01-04\n"
        "Central,150,not-a-date\n"
    )
    return SimpleUploadedFile(name, csv_content.encode("utf-8"), content_type="text/csv")


def make_intelligence_csv(name="intelligence.csv"):
    csv_content = (
        "farm_name,has_shade_trees,yield_kg,emissions_kg,report_date\n"
        "Ama Cocoa Farm,none,800,250,2024-01-01\n"
        "Ama Cocoa Farm,none,820,255,2024-02-01\n"
        "Ama Cocoa Farm,many,1200,200,2024-03-01\n"
        "Ama Cocoa Farm,many,1250,198,2024-04-01\n"
        "Ama Cocoa Farm,many,12000,190,2024-05-01\n"
    )
    return SimpleUploadedFile(name, csv_content.encode("utf-8"), content_type="text/csv")


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
        form = FarmerCreateByAgentForm(
            data=make_agent_farmer_form_data(),
            files=make_agent_farmer_form_files(),
        )
        self.assertTrue(form.is_valid())

    def test_duplicate_email_rejected(self):
        form = FarmerCreateByAgentForm(
            data=make_agent_farmer_form_data(email="existing@example.com"),
            files=make_agent_farmer_form_files(),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("already exists", form.errors["email"][0])

    def test_duplicate_email_case_insensitive(self):
        form = FarmerCreateByAgentForm(
            data=make_agent_farmer_form_data(email="EXISTING@EXAMPLE.COM"),
            files=make_agent_farmer_form_files(),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_invalid_email_format_rejected(self):
        form = FarmerCreateByAgentForm(
            data=make_agent_farmer_form_data(email="not-an-email"),
            files=make_agent_farmer_form_files(),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_duplicate_username_rejected(self):
        form = FarmerCreateByAgentForm(
            data=make_agent_farmer_form_data(username="existing", email="other@example.com"),
            files=make_agent_farmer_form_files(),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_missing_email_rejected(self):
        form = FarmerCreateByAgentForm(
            data=make_agent_farmer_form_data(email=""),
            files=make_agent_farmer_form_files(),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class FarmAssessmentSheetFormTests(TestCase):
    def test_sheet1_requires_group_name_when_farmer_belongs_to_group(self):
        form = FarmAssessmentSheet1Form(
            data={
                "full_name": "Kojo Mensah",
                "household_size": "3-5",
                "belongs_to_group": "yes",
                "farmer_group_name": "",
                "latitude": "5.603717",
                "longitude": "-0.186964",
                "location_name": "Accra",
                "land_ownership": "own",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("farmer_group_name", form.errors)

    def test_sheet1_requires_gps_coordinates(self):
        form = FarmAssessmentSheet1Form(
            data={
                "full_name": "Kojo Mensah",
                "household_size": "3-5",
                "belongs_to_group": "no",
                "farmer_group_name": "",
                "latitude": "",
                "longitude": "",
                "location_name": "",
                "land_ownership": "own",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_sheet1_save_sets_gps_captured(self):
        form = FarmAssessmentSheet1Form(
            data={
                "full_name": "Kojo Mensah",
                "household_size": "3-5",
                "belongs_to_group": "no",
                "farmer_group_name": "",
                "latitude": "5.603717",
                "longitude": "-0.186964",
                "location_name": "Accra",
                "land_ownership": "own",
            }
        )

        self.assertTrue(form.is_valid())
        assessment = form.save(commit=False)
        self.assertTrue(assessment.gps_captured)

    def test_sheet2_requires_shade_tree_type_when_shade_trees_exist(self):
        form = FarmAssessmentSheet2Form(
            data={
                "farm_size_category": "small",
                "cocoa_tree_age": "young",
                "has_shade_trees": "few",
                "shade_tree_types": "",
                "uses_fertilizer": "no",
                "fertilizer_bag_range": "none",
                "fertilizer_application": "",
                "burns_farm_waste": "never",
                "practices_agroforestry": "yes",
                "received_training": "yes",
                "plants_trees": "yes",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("shade_tree_types", form.errors)

    def test_sheet2_requires_fertilizer_details_when_enabled(self):
        form = FarmAssessmentSheet2Form(
            data={
                "farm_size_category": "small",
                "cocoa_tree_age": "young",
                "has_shade_trees": "none",
                "shade_tree_types": "",
                "uses_fertilizer": "yes",
                "fertilizer_bag_range": "none",
                "fertilizer_application": "",
                "burns_farm_waste": "never",
                "practices_agroforestry": "yes",
                "received_training": "yes",
                "plants_trees": "yes",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("fertilizer_bag_range", form.errors)
        self.assertIn("fertilizer_application", form.errors)

    def test_sheet2_clears_optional_fields_when_not_applicable(self):
        form = FarmAssessmentSheet2Form(
            data={
                "farm_size_category": "small",
                "cocoa_tree_age": "young",
                "has_shade_trees": "none",
                "shade_tree_types": "fruit",
                "uses_fertilizer": "no",
                "fertilizer_bag_range": "3-5",
                "fertilizer_application": "hand",
                "burns_farm_waste": "never",
                "practices_agroforestry": "yes",
                "received_training": "yes",
                "plants_trees": "yes",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["shade_tree_types"], "")
        self.assertEqual(form.cleaned_data["fertilizer_bag_range"], "none")
        self.assertEqual(form.cleaned_data["fertilizer_application"], "")


    def test_sheet3_requires_farmer_and_farm_photos(self):
        form = FarmAssessmentSheet3Form(
            data={
                "last_harvest_bags": "0-5",
                "harvest_compared_to_last_year": "same",
                "validation_notes": "",
            },
            files={},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("photo_of_farmer", form.errors)
        self.assertIn("photo_of_farm", form.errors)

    def test_sheet3_accepts_existing_required_photos(self):
        farmer = Farmer.objects.create_user(
            username="assessment-farmer",
            email="assessment@example.com",
            password="pass",
        )
        form = FarmAssessmentSheet3Form(
            data={
                "last_harvest_bags": "6-10",
                "harvest_compared_to_last_year": "more",
                "validation_notes": "",
            },
            files={},
            instance=FarmAssessmentSheet3(
                farmer=farmer,
                photo_of_farmer="farm_assessments/farmer_photos/existing.gif",
                photo_of_farm="farm_assessments/farm_photos/existing.gif",
            ),
        )

        self.assertTrue(form.is_valid())

    def test_sheet3_save_sets_photos_complete(self):
        form = FarmAssessmentSheet3Form(
            data={
                "last_harvest_bags": "11-20",
                "harvest_compared_to_last_year": "more",
                "validation_notes": "",
            },
            files={
                "photo_of_farmer": make_test_image("farmer.gif"),
                "photo_of_farm": make_test_image("farm.gif"),
            },
        )

        self.assertTrue(form.is_valid())
        assessment = form.save(commit=False)
        self.assertTrue(assessment.photos_complete)


class FarmerActivitySubmissionTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")
        self.agent = Farmer.objects.create_user(
            username="agent_user",
            email="agent@example.com",
            password="pass12345",
        )
        self.agent.profile.role = "field_agent"
        self.agent.profile.is_approved = True
        self.agent.profile.save(update_fields=["role", "is_approved"])

        self.farmer = Farmer.objects.create_user(
            username="farmer_user",
            email="farmer@example.com",
            password="pass12345",
        )
        self.farmer.profile.role = "farmer"
        self.farmer.profile.is_approved = True
        self.farmer.profile.created_by_agent = self.agent
        self.farmer.profile.save(update_fields=["role", "is_approved", "created_by_agent"])

    @patch("Farmers.views.Message.objects.create", side_effect=IntegrityError("FOREIGN KEY constraint failed"))
    def test_submit_activity_gracefully_handles_message_integrity_error(self, _mock_message_create):
        self.client.force_login(self.farmer)

        response = self.client.post(
            reverse("submit_farmer_activity"),
            {
                "activity_type": "planting",
                "date": "2026-05-20",
                "additional_trees_added": "0",
                "inputs_used": "Seedlings",
                "quantity": "5",
                "notes": "Regression test",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("farmer_dashboard"))
        self.assertEqual(FarmActivity.objects.filter(farmer=self.farmer).count(), 1)
        self.assertEqual(Message.objects.filter(sender=self.farmer, receiver=self.agent).count(), 0)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.agent,
                notification_type="message",
                title__contains="New activity from",
            ).exists()
        )


class CreateFarmerViewTests(TestCase):
    """Tests for the create_farmer view used by field agents."""

    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()
        self.client = Client()
        self.agent = Farmer.objects.create_user(
            username="agent1", email="agent@example.com", password="agentpass"
        )
        self.agent_profile = self.agent.profile
        self.agent_profile.role = "field_agent"
        self.agent_profile.is_approved = True
        self.agent_profile.save()

    def tearDown(self):
        self.media_override.disable()
        self.temp_media.cleanup()

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
        response = self.client.post(
            reverse("create_farmer"),
            make_agent_farmer_form_payload(email="newfarmer@example.com"),
        )
        self.assertRedirects(response, reverse("agent_dashboard"))
        farmer = Farmer.objects.get(username="newfarmer")
        self.assertEqual(farmer.email, "newfarmer@example.com")
        self.assertFalse(farmer.has_usable_password())
        self.assertFalse(farmer.profile.is_approved)
        self.assertEqual(farmer.profile.role, "farmer")
        self.assertTrue(FarmAssessmentSheet1.objects.filter(farmer=farmer, gps_captured=True).exists())
        self.assertTrue(FarmAssessmentSheet2.objects.filter(farmer=farmer).exists())
        self.assertTrue(FarmAssessmentSheet3.objects.filter(farmer=farmer, photos_complete=True).exists())

    def test_duplicate_email_shows_error(self):
        Farmer.objects.create_user(username="existing", email="taken@example.com", password="pass")
        self.client.force_login(self.agent)
        response = self.client.post(
            reverse("create_farmer"),
            make_agent_farmer_form_payload(username="anotherfarmer", email="taken@example.com"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")


class PartnerDatasetImportTests(TestCase):
    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()

        self.client = Client()
        self.investor = Farmer.objects.create_user(
            username="investor1",
            email="investor@example.com",
            password="investorpass",
        )
        self.investor.profile.role = "investor"
        self.investor.profile.is_approved = True
        self.investor.profile.save()

        self.analyst = Farmer.objects.create_user(
            username="analyst1",
            email="analyst@example.com",
            password="analystpass",
        )
        self.analyst.profile.role = "analyst"
        self.analyst.profile.is_approved = True
        self.analyst.profile.save()

        self.admin_user = Farmer.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password="adminpass",
        )
        self.admin_user.profile.role = "admin"
        self.admin_user.profile.is_approved = True
        self.admin_user.profile.save()

        self.other_investor = Farmer.objects.create_user(
            username="investor2",
            email="investor2@example.com",
            password="investor2pass",
        )
        self.other_investor.profile.role = "investor"
        self.other_investor.profile.is_approved = True
        self.other_investor.profile.save()

        self.portfolio_farmer = Farmer.objects.create_user(
            username="ama",
            email="ama@example.com",
            password="farmerpass",
        )
        self.portfolio_farm = Farm.objects.create(
            name="Ama Cocoa Farm",
            owner=self.portfolio_farmer,
            location="Accra",
            size_in_hectares=2.5,
        )
        Harvest.objects.create(
            farm=self.portfolio_farm,
            date_of_harvest="2024-01-12",
            tons_produced=1.2,
            quality_grade="A",
        )
        Investment.objects.create(
            investor=self.investor,
            farm=self.portfolio_farm,
            amount=5000,
            expected_return_percentage=12,
        )

    def tearDown(self):
        self.media_override.disable()
        self.temp_media.cleanup()

    def test_preview_upload_creates_draft_dataset_and_clean_rows(self):
        self.client.force_login(self.investor)
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Quarterly Portfolio",
                "data_file": make_test_csv(),
            },
        )

        self.assertEqual(response.status_code, 302)
        draft = InvestorDatasetImport.objects.get(investor=self.investor, status="draft")
        self.assertEqual(draft.dataset_name, "Quarterly Portfolio")
        self.assertEqual(draft.file_format, "csv")
        self.assertEqual(draft.stats["total_rows_read"], 4)
        self.assertEqual(draft.stats["rows_after_dedup"], 3)
        self.assertEqual(draft.stats["duplicate_rows_removed"], 1)
        self.assertIn("aggregated_columns", draft.stats)
        self.assertIn("columnar_storage", draft.stats)
        self.assertIn("yield_kg", draft.stats["aggregated_columns"])
        self.assertIn("columns", draft.stats["columnar_storage"])
        self.assertIn("yield_kg", draft.stats["columnar_storage"]["columns"])
        self.assertIn("semantic_model", draft.stats)
        semantic_model = draft.stats["semantic_model"]
        self.assertIn("relationships", semantic_model)
        self.assertIn("table_suggestions", semantic_model)
        self.assertIn("computed_metrics", semantic_model)
        self.assertIn("dax_like_measures", semantic_model)
        self.assertIn("cross_analysis", semantic_model)
        self.assertIn("yield_vs_emissions", semantic_model["cross_analysis"])
        self.assertIn("practices_vs_profitability", semantic_model["cross_analysis"])
        self.assertIn("region_vs_deforestation_risk", semantic_model["cross_analysis"])
        self.assertGreaterEqual(semantic_model["cross_analysis"]["merge_summary"]["linked_rows"], 1)
        self.assertTrue(InvestorDatasetRow.objects.filter(dataset=draft).exists())

    def test_import_action_marks_draft_as_imported(self):
        self.client.force_login(self.investor)
        self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Quarterly Portfolio",
                "data_file": make_test_csv(),
            },
        )
        draft = InvestorDatasetImport.objects.get(investor=self.investor, status="draft")

        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "import",
                "batch_id": draft.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "imported")
        self.assertIsNotNone(draft.imported_at)

    def test_load_existing_action_redirects_to_preview(self):
        self.client.force_login(self.investor)
        self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Dataset A",
                "data_file": make_test_csv(name="dataset_a.csv"),
            },
        )
        draft = InvestorDatasetImport.objects.get(investor=self.investor, status="draft")

        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "import",
                "batch_id": draft.id,
            },
        )
        self.assertEqual(response.status_code, 302)

        imported_batch = InvestorDatasetImport.objects.get(pk=draft.id, investor=self.investor)
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "load_existing",
                "batch_id": imported_batch.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"preview_id={imported_batch.id}", response.url)

    def test_delete_existing_action_removes_dataset(self):
        self.client.force_login(self.investor)
        self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Dataset To Delete",
                "data_file": make_test_csv(name="dataset_delete.csv"),
            },
        )
        draft = InvestorDatasetImport.objects.get(investor=self.investor, status="draft")

        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "delete_existing",
                "batch_id": draft.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(InvestorDatasetImport.objects.filter(pk=draft.id).exists())

    def test_type_inference_tolerates_noisy_values_for_numeric_and_date_columns(self):
        self.client.force_login(self.investor)
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Noisy Types",
                "data_file": make_noisy_type_csv(),
            },
        )

        self.assertEqual(response.status_code, 302)
        draft = InvestorDatasetImport.objects.get(investor=self.investor, status="draft")
        schema_by_col = {col["column"]: col for col in draft.schema}
        self.assertEqual(schema_by_col["amount"]["type"], "integer")
        self.assertEqual(schema_by_col["report_date"]["type"], "date")

    def test_save_layout_persists_investor_dashboard_layout(self):
        self.client.force_login(self.investor)
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "save_layout",
                "layout_payload": "{\"top\":[\"overview\",\"risk\"],\"middle\":[\"trends\"],\"bottom\":[]}",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.investor.profile.refresh_from_db()
        self.assertEqual(self.investor.profile.dashboard_layout.get("top"), ["overview", "risk"])
        self.assertEqual(self.investor.profile.dashboard_layout.get("middle"), ["trends"])
        self.assertEqual(self.investor.profile.dashboard_layout.get("bottom"), [])

    def test_save_layout_with_invalid_json_does_not_update_profile(self):
        self.client.force_login(self.investor)
        self.investor.profile.dashboard_layout = {"top": ["overview"], "middle": [], "bottom": []}
        self.investor.profile.save(update_fields=["dashboard_layout"])

        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "save_layout",
                "layout_payload": "not-json",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.investor.profile.refresh_from_db()
        self.assertEqual(self.investor.profile.dashboard_layout.get("top"), ["overview"])

    def test_upload_preview_creates_audit_log(self):
        self.client.force_login(self.investor)
        self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Audit Portfolio",
                "data_file": make_test_csv(name="audit.csv"),
            },
        )

        self.assertTrue(
            DatasetAuditLog.objects.filter(actor=self.investor, action="upload_preview").exists()
        )

    def test_save_layout_creates_audit_log(self):
        self.client.force_login(self.investor)
        self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "save_layout",
                "layout_payload": "{\"top\":[\"overview\"],\"middle\":[],\"bottom\":[]}",
            },
        )

        self.assertTrue(
            DatasetAuditLog.objects.filter(actor=self.investor, action="save_layout").exists()
        )

    def test_analyst_can_access_external_analysis(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse("partner_external_analysis"))
        self.assertEqual(response.status_code, 200)

    def test_cross_user_dataset_actions_are_rejected_without_success_audit_events(self):
        self.client.force_login(self.other_investor)
        self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Other Investor Dataset",
                "data_file": make_test_csv(name="other_investor.csv"),
            },
        )
        other_draft = InvestorDatasetImport.objects.get(investor=self.other_investor, status="draft")

        self.client.force_login(self.investor)
        blocked_actions = ["load_existing", "delete_existing", "import"]
        for action in blocked_actions:
            response = self.client.post(
                reverse("partner_dataset_upload"),
                {
                    "action": action,
                    "batch_id": other_draft.id,
                },
            )
            self.assertEqual(response.status_code, 404)

        self.assertEqual(
            DatasetAuditLog.objects.filter(actor=self.investor, action__in=blocked_actions).count(),
            0,
        )

        other_draft.refresh_from_db()
        self.assertEqual(other_draft.status, "draft")

    def test_admin_and_analyst_can_view_audit_log_page(self):
        self.client.force_login(self.admin_user)
        admin_response = self.client.get(reverse("dataset_audit_log_viewer"))
        self.assertEqual(admin_response.status_code, 200)

        self.client.force_login(self.analyst)
        analyst_response = self.client.get(reverse("dataset_audit_log_viewer"))
        self.assertEqual(analyst_response.status_code, 200)

    def test_investor_cannot_view_audit_log_page(self):
        self.client.force_login(self.investor)
        response = self.client.get(reverse("dataset_audit_log_viewer"))
        self.assertEqual(response.status_code, 403)

    def test_audit_log_viewer_paginates_results(self):
        logs_to_create = [
            DatasetAuditLog(actor=self.investor, action="save_layout", details={"idx": idx})
            for idx in range(55)
        ]
        DatasetAuditLog.objects.bulk_create(logs_to_create)

        self.client.force_login(self.admin_user)
        page_one = self.client.get(reverse("dataset_audit_log_viewer"))
        self.assertEqual(page_one.status_code, 200)
        self.assertEqual(page_one.context["paginator"].num_pages, 2)
        self.assertEqual(page_one.context["page_obj"].number, 1)
        self.assertEqual(len(page_one.context["logs"]), 50)

        page_two = self.client.get(reverse("dataset_audit_log_viewer"), {"page": 2})
        self.assertEqual(page_two.status_code, 200)
        self.assertEqual(page_two.context["page_obj"].number, 2)
        self.assertEqual(len(page_two.context["logs"]), 5)

    def test_audit_log_viewer_filters_by_date_range(self):
        old_log = DatasetAuditLog.objects.create(
            actor=self.investor,
            action="save_layout",
            details={"marker": "old"},
        )
        DatasetAuditLog.objects.filter(pk=old_log.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        recent_log = DatasetAuditLog.objects.create(
            actor=self.investor,
            action="save_layout",
            details={"marker": "recent"},
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("dataset_audit_log_viewer"),
            {
                "start_date": (timezone.now() - timedelta(days=2)).date().isoformat(),
                "end_date": timezone.now().date().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)

        returned_ids = [log.id for log in response.context["logs"]]
        self.assertIn(recent_log.id, returned_ids)
        self.assertNotIn(old_log.id, returned_ids)

    def test_advanced_intelligence_sections_are_generated(self):
        self.client.force_login(self.investor)
        preview_response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Intelligence Dataset",
                "data_file": make_intelligence_csv(),
            },
        )
        self.assertEqual(preview_response.status_code, 302)

        draft = InvestorDatasetImport.objects.get(investor=self.investor, status="draft")
        response = self.client.get(reverse("partner_external_analysis"), {"preview_id": draft.id})
        self.assertEqual(response.status_code, 200)

        analytics = response.context["dataset_analytics"]
        self.assertTrue(analytics["auto_insights"])
        insight_texts = [item["detail"] for item in analytics["auto_insights"]]
        self.assertTrue(any("Yield is lower in farms with no shade trees" in text for text in insight_texts))

        self.assertIn("anomalies", analytics)
        self.assertIsInstance(analytics["anomalies"], list)
        if analytics["anomalies"]:
            self.assertIn("column", analytics["anomalies"][0])
            self.assertIn("z_score", analytics["anomalies"][0])

        predictive = analytics["predictive_modeling"]
        self.assertIn("yield_forecast", predictive)
        self.assertIn("carbon_trend_forecast", predictive)
        self.assertIsNotNone(predictive["yield_forecast"])


class PowerBIEmbeddedTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.investor = Farmer.objects.create_user(
            username="powerbi_investor",
            email="powerbi.investor@example.com",
            password="pass1234",
        )
        self.investor.profile.role = "investor"
        self.investor.profile.is_approved = True
        self.investor.profile.save()

        self.analyst = Farmer.objects.create_user(
            username="powerbi_analyst",
            email="powerbi.analyst@example.com",
            password="pass1234",
        )
        self.analyst.profile.role = "analyst"
        self.analyst.profile.is_approved = True
        self.analyst.profile.save()

    def test_powerbi_page_is_available_to_investor(self):
        self.client.force_login(self.investor)
        response = self.client.get(reverse("partner_powerbi_embedded"))
        self.assertEqual(response.status_code, 200)

    @override_settings(
        POWER_BI_TENANT_ID="tenant",
        POWER_BI_CLIENT_ID="client",
        POWER_BI_CLIENT_SECRET="secret",
        POWER_BI_WORKSPACE_ID="workspace",
        POWER_BI_REPORT_ID="report",
        POWER_BI_DATASET_ID="dataset",
    )
    @patch("Farmers.views.PowerBIService.get_embed_config")
    def test_embed_config_endpoint_returns_payload(self, mock_get_embed_config):
        mock_get_embed_config.return_value = {
            "reportId": "report",
            "reportName": "Investor Intelligence",
            "embedUrl": "https://app.powerbi.com/reportEmbed",
            "embedToken": "embed-token",
            "datasetId": "dataset",
        }
        self.client.force_login(self.investor)
        response = self.client.get(reverse("partner_powerbi_embed_config"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["config"]["reportId"], "report")

    @override_settings(
        POWER_BI_TENANT_ID="tenant",
        POWER_BI_CLIENT_ID="client",
        POWER_BI_CLIENT_SECRET="secret",
        POWER_BI_WORKSPACE_ID="workspace",
        POWER_BI_REPORT_ID="report",
        POWER_BI_DATASET_ID="dataset",
    )
    @patch("Farmers.views.PowerBIService.refresh_dataset")
    def test_refresh_endpoint_allows_analyst(self, mock_refresh):
        mock_refresh.return_value = {
            "status": "submitted",
            "requestId": "req-123",
            "datasetId": "dataset",
        }
        self.client.force_login(self.analyst)
        response = self.client.post(reverse("partner_powerbi_refresh_dataset"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["refresh"]["requestId"], "req-123")

    def test_refresh_endpoint_rejects_investor(self):
        self.client.force_login(self.investor)
        response = self.client.post(reverse("partner_powerbi_refresh_dataset"))
        self.assertEqual(response.status_code, 403)


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
            self.assertEqual(mail.outbox[0].from_email, "admin@example.com")


class PasswordResetLinkEmailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Farmer.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="adminpass",
        )
        self.admin.profile.role = "admin"
        self.admin.profile.is_approved = True
        self.admin.profile.save()

        self.target_user = Farmer.objects.create_user(
            username="yawgalo",
            email="yaw@example.com",
            password="temp12345",
            is_active=True,
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_generate_password_reset_link_sends_email_and_completes_request(self):
        self.client.force_login(self.admin)
        reset_request = PasswordResetRequest.objects.create(
            user=self.target_user,
            requested_by_username=self.target_user.username,
            requested_by_email=self.target_user.email,
            status="pending",
        )

        response = self.client.post(
            reverse("generate_password_reset_link", args=[self.target_user.id])
        )

        self.assertRedirects(response, reverse("admin_dashboard"))
        reset_request.refresh_from_db()
        self.assertEqual(reset_request.status, "completed")
        self.assertEqual(reset_request.processed_by, self.admin)
        self.assertIsNotNone(reset_request.processed_at)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.target_user.email, mail.outbox[0].to)
        self.assertIn("password reset", mail.outbox[0].subject.lower())
        self.assertIn("/reset/", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].from_email, self.admin.email)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_generate_password_reset_link_email_failure_keeps_request_pending(self):
        from unittest.mock import patch

        self.client.force_login(self.admin)
        reset_request = PasswordResetRequest.objects.create(
            user=self.target_user,
            requested_by_username=self.target_user.username,
            requested_by_email=self.target_user.email,
            status="pending",
        )

        with patch("Farmers.views.send_mail", side_effect=Exception("smtp down")):
            response = self.client.post(
                reverse("generate_password_reset_link", args=[self.target_user.id])
            )

        self.assertRedirects(response, reverse("admin_dashboard"))
        reset_request.refresh_from_db()
        self.assertEqual(reset_request.status, "pending")
        self.assertIsNone(reset_request.processed_by)
        self.assertIsNone(reset_request.processed_at)


class CreateUserSenderEmailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Farmer.objects.create_user(
            username="ops_admin",
            email="ops-admin@example.com",
            password="adminpass",
        )
        self.admin.profile.role = "admin"
        self.admin.profile.is_approved = True
        self.admin.profile.save()

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_create_user_uses_acting_admin_as_sender(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("create_user"),
            {
                "username": "newpartner",
                "email": "newpartner@example.com",
                "first_name": "New",
                "last_name": "Partner",
                "role": "investor",
            },
        )

        self.assertRedirects(response, reverse("admin_dashboard"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("newpartner@example.com", mail.outbox[0].to)
        self.assertEqual(mail.outbox[0].from_email, self.admin.email)


class ContactReplyLinkValidationTests(TestCase):
    def test_contact_reply_email_validation_rejects_header_injection(self):
        from Farmers.views import _is_valid_contact_reply_email

        self.assertFalse(_is_valid_contact_reply_email("guest@example.com\nBcc:evil@example.com"))

    def test_contact_reply_mailto_builder_targets_guest_email(self):
        from Farmers.views import _build_contact_reply_mailto

        mailto_url = _build_contact_reply_mailto("Guest@Example.com", "Guest User")
        self.assertTrue(mailto_url.startswith("mailto:guest@example.com?"))
        self.assertIn("Re%3A%20Your%20Contact%20Us%20Request%20to%201847%20Ventures", mailto_url)
        self.assertIn("Guest%20User", mailto_url)


class HomeContactSubmissionReplyEmailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Farmer.objects.create_user(
            username="contact_admin",
            email="contact-admin@example.com",
            password="adminpass",
        )
        self.admin.profile.role = "admin"
        self.admin.profile.is_approved = True
        self.admin.profile.save(update_fields=["role", "is_approved"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_home_contact_submission_email_contains_reply_link(self):
        response = self.client.post(
            reverse("home"),
            {
                "name": "Public Guest",
                "email": "guest-public@example.com",
                "phone": "+231 77 000 0000",
                "nationel": "Liberian",
                "current_resident": "Liberia",
                "reason_for_contact": "I would like more details about the program.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("contact-admin@example.com", sent.to)
        self.assertIn("mailto:guest-public@example.com", sent.body)
        self.assertTrue(sent.alternatives)
        self.assertIn("Reply to Guest", sent.alternatives[0][0])
        self.assertIn("mailto:guest-public@example.com", sent.alternatives[0][0])


class DataPrepTests(TestCase):
    """Tests for data preparation workspace and column/row operations."""

    def setUp(self):
        self.client = Client()
        self.investor = Farmer.objects.create_user(
            username="dataprep_investor",
            email="dataprep@example.com",
            password="testpass",
        )
        self.investor.profile.role = "investor"
        self.investor.profile.is_approved = True
        self.investor.profile.save()

        self.client.force_login(self.investor)

        # Create a test dataset using existing test CSV
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Test Data",
                "data_file": make_test_csv(),
            },
        )

        self.dataset = InvestorDatasetImport.objects.filter(
            investor=self.investor,
            status="draft",
        ).first()

    def test_column_rename_operation(self):
        """Test column renaming."""
        self.assertIsNotNone(self.dataset)

        response = self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "rename",
                "column_name": "farmer_name",
                "new_name": "farmer_identifier",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["operation"], "rename")

        # Verify metadata was saved
        self.dataset.refresh_from_db()
        self.assertIn("farmer_name", self.dataset.column_metadata)
        self.assertEqual(
            self.dataset.column_metadata["farmer_name"]["rename"],
            "farmer_identifier",
        )

    def test_column_hide_operation(self):
        """Test hiding a column."""
        response = self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "hide",
                "column_name": "is_active",
                "hidden": "true",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertTrue(self.dataset.column_metadata["is_active"]["hidden"])

    def test_column_retype_operation(self):
        """Test changing column data type."""
        response = self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "retype",
                "column_name": "yield_kg",
                "new_type": "numeric",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertEqual(
            self.dataset.column_metadata["yield_kg"]["type_override"],
            "numeric",
        )

    def test_column_semantic_tag_operation(self):
        """Test tagging column with semantic meaning."""
        response = self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "semantic_tag",
                "column_name": "yield_kg",
                "semantic_tag": "measure",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertEqual(
            self.dataset.column_metadata["yield_kg"]["semantic_tag"],
            "measure",
        )

    def test_column_remove_operation(self):
        """Test removing a column."""
        response = self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "remove",
                "column_name": "is_active",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertTrue(self.dataset.column_metadata["is_active"]["removed"])

    def test_column_remove_operation_works_for_imported_dataset(self):
        """Removing a column should work for owned datasets beyond draft status."""
        self.dataset.status = "imported"
        self.dataset.save(update_fields=["status"])

        response = self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "remove",
                "column_name": "is_active",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertTrue(self.dataset.column_metadata["is_active"]["removed"])

    def test_row_filter_operation(self):
        """Test adding a row filter."""
        response = self.client.post(
            reverse("data_prep_row_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "add_filter",
                "column": "farmer_name",
                "operator": "equals",
                "value": "Ama",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertIn("filters", self.dataset.row_operations)
        self.assertEqual(len(self.dataset.row_operations["filters"]), 1)

    def test_row_exclude_nulls_operation(self):
        """Test excluding rows with null values."""
        response = self.client.post(
            reverse("data_prep_row_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "exclude_nulls",
                "columns": "farmer_name,yield_kg",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertIn("exclude_nulls", self.dataset.row_operations)

    def test_row_remove_duplicates_operation(self):
        """Test removing duplicate rows."""
        response = self.client.post(
            reverse("data_prep_row_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "remove_duplicates",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        self.dataset.refresh_from_db()
        self.assertTrue(self.dataset.row_operations.get("remove_duplicates"))

    def test_data_prep_preview_endpoint(self):
        """Test getting live preview of data prep changes."""
        response = self.client.get(
            reverse("data_prep_preview"),
            {
                "dataset_id": self.dataset.id,
                "limit": "10",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("schema", data)
        self.assertIn("rows", data)
        self.assertIn("row_count", data)

    def test_dataset_analysis_state_get_defaults(self):
        """Analysis state endpoint returns normalized defaults for a dataset."""
        response = self.client.get(
            reverse("dataset_analysis_state"),
            {"dataset_id": self.dataset.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("state", payload)
        self.assertIn("data_state", payload["state"])
        self.assertIn("visualization_state", payload["state"])
        self.assertIn("active_dataset_transformations", payload["state"]["data_state"])

    def test_dataset_analysis_state_persists_visualization_state(self):
        """Changing chart configuration should persist without mutating data transforms."""
        state_payload = {
            "version": 1,
            "data_state": {
                "filters": [{"column": "farmer_name", "operator": "equals", "value": "Ama"}],
                "drill_through_context": ["region:Ashanti"],
                "selected_metrics": ["yield_kg"],
                "hierarchy_state": {"region": ["Ashanti"]},
                "slicers": {"year": "2024"},
                "active_dataset_transformations": {"column_metadata": {}, "row_operations": {}},
            },
            "visualization_state": {
                "chart_types": {"dist-chart-0": "pie"},
                "active_view": "charts",
            },
        }

        response = self.client.post(
            reverse("dataset_analysis_state"),
            {
                "dataset_id": self.dataset.id,
                "state": json.dumps(state_payload),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["state"]["visualization_state"]["chart_types"].get("dist-chart-0"),
            "pie",
        )

        self.dataset.refresh_from_db()
        saved_engine_state = (self.dataset.prep_state or {}).get("analytics_engine", {})
        self.assertEqual(
            saved_engine_state.get("visualization_state", {}).get("chart_types", {}).get("dist-chart-0"),
            "pie",
        )
        self.assertIn("active_dataset_transformations", saved_engine_state.get("data_state", {}))

    def test_data_prep_workspace_view(self):
        """Test rendering the data prep workspace."""
        response = self.client.get(
            reverse("data_prep_workspace"),
            {"preview_id": self.dataset.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Data Preparation Workspace", response.content)
        self.assertIn(b"farmer_name", response.content)

    def test_undo_redo_operations(self):
        """Test undo/redo functionality."""
        # Perform a column operation
        self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "rename",
                "column_name": "farmer_name",
                "new_name": "farmer_code",
            },
        )

        self.dataset.refresh_from_db()
        initial_history_len = len(self.dataset.prep_history or [])
        self.assertGreater(initial_history_len, 0)

    def test_unauthorized_user_cannot_access_data_prep(self):
        """Test that unauthorized users cannot access data prep."""
        other_investor = Farmer.objects.create_user(
            username="other_investor",
            email="other@example.com",
            password="testpass",
        )
        other_investor.profile.role = "investor"
        other_investor.profile.is_approved = True
        other_investor.profile.save()

        self.client.force_login(other_investor)

        response = self.client.post(
            reverse("data_prep_column_operation"),
            {
                "dataset_id": self.dataset.id,
                "operation": "rename",
                "column_name": "farmer_name",
                "new_name": "farmer_code",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_analyst_can_access_data_prep(self):
        """Test that analysts can also access data prep."""
        analyst = Farmer.objects.create_user(
            username="analyst1",
            email="analyst@example.com",
            password="testpass",
        )
        analyst.profile.role = "analyst"
        analyst.profile.is_approved = True
        analyst.profile.save()

        # Create a dataset for the analyst
        self.client.force_login(analyst)
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "action": "preview",
                "dataset_name": "Analyst Data",
                "data_file": make_test_csv("analyst_data.csv"),
            },
        )

        analyst_dataset = InvestorDatasetImport.objects.filter(
            investor=analyst,
            status="draft",
        ).first()

        response = self.client.get(
            reverse("data_prep_workspace"),
            {"preview_id": analyst_dataset.id},
        )

        self.assertEqual(response.status_code, 200)


class FarmerDashboardAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("farmer_dashboard")

        self.farmer = Farmer.objects.create_user(
            username="dash_farmer",
            email="dash_farmer@example.com",
            password="testpass",
        )
        self.farmer.profile.role = "farmer"
        self.farmer.profile.is_approved = True
        self.farmer.profile.save()

        self.agent = Farmer.objects.create_user(
            username="dash_agent",
            email="dash_agent@example.com",
            password="testpass",
        )
        self.agent.profile.role = "field_agent"
        self.agent.profile.is_approved = True
        self.agent.profile.save()

        self.investor = Farmer.objects.create_user(
            username="dash_investor",
            email="dash_investor@example.com",
            password="testpass",
        )
        self.investor.profile.role = "investor"
        self.investor.profile.is_approved = True
        self.investor.profile.save()

    def test_farmer_can_access_farmer_dashboard(self):
        self.client.force_login(self.farmer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_field_agent_redirects_to_agent_dashboard(self):
        self.client.force_login(self.agent)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("agent_dashboard"))

    def test_investor_redirects_to_partner_dashboard(self):
        self.client.force_login(self.investor)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("partner_dashboard"))


class AdminDashboardNotificationActionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Farmer.objects.create_user(
            username="admin_actions",
            email="admin.actions@example.com",
            password="adminpass",
            is_active=True,
        )
        self.admin.profile.role = "admin"
        self.admin.profile.is_approved = True
        self.admin.profile.save(update_fields=["role", "is_approved"])

        self.agent = Farmer.objects.create_user(
            username="jackson",
            email="jackson.agent@example.com",
            password="agentpass",
            is_active=True,
        )
        self.agent.profile.role = "field_agent"
        self.agent.profile.is_approved = True
        self.agent.profile.save(update_fields=["role", "is_approved"])

        self.farmer = Farmer.objects.create_user(
            username="YGalo",
            email="ygalo@example.com",
            password="farmerpass",
            is_active=True,
        )
        self.farmer.profile.role = "farmer"
        self.farmer.profile.is_approved = True
        self.farmer.profile.created_by_agent = self.agent
        self.farmer.profile.save(update_fields=["role", "is_approved", "created_by_agent"])

    def test_activity_notification_shows_approve_button(self):
        activity = FarmActivity.objects.create(
            farmer=self.farmer,
            activity_type="harvesting",
            date=timezone.now().date(),
            verification_status="verified",
            admin_approval_status="pending",
            verified_by=self.agent,
            verified_at=timezone.now(),
        )

        AdminNotification.objects.create(
            recipient=self.admin,
            notification_type="info",
            message=(
                "Field agent jackson verified activity for farmer "
                "YGalo: Harvesting."
            ),
            related_farmer=self.farmer,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("approve_farmer_activity", args=[activity.pk]))
        self.assertContains(response, "Approve")

    def test_contact_notification_shows_reply_button(self):
        AdminNotification.objects.create(
            recipient=self.admin,
            notification_type="info",
            message=(
                "New homepage Contact Us request received.\n"
                "Name: Prince Jackson Kpadeh, Jr.\n"
                "Email: jacksonkpadehjr@gmail.com\n"
                "Phone: 0531257922\n"
                "Nationel: Liberian\n"
                "Current Resident: Accra, Ghana\n"
                "Reason: I have a cocoa farm."
            ),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mailto:jacksonkpadehjr@gmail.com?")
        self.assertContains(response, "Reply")


class LoginSignalTests(TestCase):
    def test_unapproved_user_is_logged_out_after_login(self):
        user = Farmer.objects.create_user(
            username="pending_signal_user",
            email="pending_signal@example.com",
            password="testpass",
        )
        user.profile.is_approved = False
        user.profile.save(update_fields=["is_approved"])

        login_ok = self.client.login(username="pending_signal_user", password="testpass")
        self.assertTrue(login_ok)

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)



# =====================================================================
# Domain Classification Tests
# =====================================================================
class DatasetDomainClassificationTests(TestCase):
    """Test domain classification for uploaded datasets."""
    
    def setUp(self):
        self.client = Client()
        self.investor = Farmer.objects.create_user(
            username="investor", email="investor@example.com", password="testpass"
        )
        self.investor.profile.role = "investor"
        self.investor.profile.is_approved = True
        self.investor.profile.save()
    
    def test_agriculture_domain_detection(self):
        """Test that agriculture datasets are correctly classified."""
        from Farmers.semantic_modeling import detect_dataset_domain
        
        schema = [
            {"column": "farm_id", "type": "string"},
            {"column": "yield_kg", "type": "numeric"},
            {"column": "hectares", "type": "numeric"},
            {"column": "harvest_date", "type": "date"},
        ]
        rows = [
            {"farm_id": "F1", "yield_kg": 100, "hectares": 5, "harvest_date": "2024-01-15"}
        ]
        
        result = detect_dataset_domain(schema, rows)
        
        self.assertEqual(result["inferred_domain"], "agriculture")
        self.assertGreater(result["confidence"], 0.5)
        self.assertIn("agriculture", result["domain_scores"])
    
    def test_finance_domain_detection(self):
        """Test that finance datasets are correctly classified."""
        from Farmers.semantic_modeling import detect_dataset_domain
        
        schema = [
            {"column": "invoice_id", "type": "string"},
            {"column": "revenue", "type": "numeric"},
            {"column": "expense", "type": "numeric"},
            {"column": "profit", "type": "numeric"},
        ]
        rows = [
            {"invoice_id": "INV001", "revenue": 1000, "expense": 600, "profit": 400}
        ]
        
        result = detect_dataset_domain(schema, rows)
        
        self.assertEqual(result["inferred_domain"], "finance")
        self.assertGreater(result["domain_scores"]["finance"], 0.5)
    
    def test_carbon_esg_domain_detection(self):
        """Test that carbon/ESG datasets are correctly classified."""
        from Farmers.semantic_modeling import detect_dataset_domain
        
        schema = [
            {"column": "facility_id", "type": "string"},
            {"column": "co2_emissions", "type": "numeric"},
            {"column": "carbon_offset", "type": "numeric"},
            {"column": "scope", "type": "string"},
        ]
        rows = [
            {"facility_id": "F1", "co2_emissions": 500, "carbon_offset": 100, "scope": "1"}
        ]
        
        result = detect_dataset_domain(schema, rows)
        
        self.assertEqual(result["inferred_domain"], "carbon_esg")
        self.assertGreater(result["domain_scores"]["carbon_esg"], 0.5)
    
    def test_hr_domain_detection(self):
        """Test that HR datasets are correctly classified."""
        from Farmers.semantic_modeling import detect_dataset_domain
        
        schema = [
            {"column": "employee_id", "type": "string"},
            {"column": "salary", "type": "numeric"},
            {"column": "department", "type": "string"},
            {"column": "hire_date", "type": "date"},
        ]
        rows = [
            {"employee_id": "E1", "salary": 50000, "department": "Sales", "hire_date": "2020-01-01"}
        ]
        
        result = detect_dataset_domain(schema, rows)
        
        self.assertEqual(result["inferred_domain"], "hr")
        self.assertGreater(result["domain_scores"]["hr"], 0.5)
    
    def test_inventory_domain_detection(self):
        """Test that inventory datasets are correctly classified."""
        from Farmers.semantic_modeling import detect_dataset_domain
        
        schema = [
            {"column": "sku", "type": "string"},
            {"column": "stock_level", "type": "numeric"},
            {"column": "warehouse", "type": "string"},
            {"column": "units", "type": "numeric"},
        ]
        rows = [
            {"sku": "SKU001", "stock_level": 100, "warehouse": "WH1", "units": 50}
        ]
        
        result = detect_dataset_domain(schema, rows)
        
        self.assertEqual(result["inferred_domain"], "inventory")
        self.assertGreater(result["domain_scores"]["inventory"], 0.5)
    
    def test_domain_scores_all_present(self):
        """Test that all domain scores are present in the result."""
        from Farmers.semantic_modeling import detect_dataset_domain
        
        schema = [{"column": "data", "type": "string"}]
        rows = [{"data": "test"}]
        
        result = detect_dataset_domain(schema, rows)
        
        expected_domains = {"agriculture", "finance", "hr", "inventory", "carbon_esg", "general"}
        self.assertEqual(set(result["domain_scores"].keys()), expected_domains)
    
    def test_domain_confidence_is_float(self):
        """Test that confidence is a valid float between 0 and 1."""
        from Farmers.semantic_modeling import detect_dataset_domain
        
        schema = [{"column": "yield", "type": "numeric"}]
        rows = [{"yield": 100}]
        
        result = detect_dataset_domain(schema, rows)
        
        self.assertIsInstance(result["confidence"], float)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
    
    def test_domain_persisted_after_upload(self):
        """Test that inferred domain is persisted to the database after upload."""
        self.client.force_login(self.investor)
        
        csv_data = "farm_id,yield_kg,hectares\nF1,100,5\nF2,150,7"
        csv_file = SimpleUploadedFile(
            "test.csv",
            csv_data.encode(),
            content_type="text/csv"
        )
        
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {
                "data_file": csv_file,
                "dataset_name": "Test Agricultural Data",
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        dataset = InvestorDatasetImport.objects.filter(investor=self.investor).first()
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.inferred_domain, "agriculture")
        self.assertGreater(dataset.inferred_domain_confidence, 0)
        self.assertIn("agriculture", dataset.inferred_domain_scores)
    
    def test_confirm_domain_classification_endpoint(self):
        """Test the endpoint for confirming domain classification."""
        self.client.force_login(self.investor)
        
        # First, upload a dataset
        csv_data = "revenue,profit\n1000,500"
        csv_file = SimpleUploadedFile("test.csv", csv_data.encode(), content_type="text/csv")
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {"data_file": csv_file, "dataset_name": "Test Finance Data"}
        )
        
        dataset = InvestorDatasetImport.objects.filter(investor=self.investor).first()
        
        # Now confirm the domain classification
        response = self.client.post(
            reverse("confirm_dataset_domain_classification"),
            {
                "dataset_id": dataset.id,
                "confirmed_domain": "finance",
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["confirmed_domain"], "finance")
        
        dataset.refresh_from_db()
        self.assertEqual(dataset.confirmed_domain, "finance")

    def test_confirm_domain_classification_for_imported_dataset(self):
        """Domain confirmation should also work for imported datasets reopened for analysis."""
        self.client.force_login(self.investor)

        csv_data = "revenue,profit\n1000,500"
        csv_file = SimpleUploadedFile("test.csv", csv_data.encode(), content_type="text/csv")
        self.client.post(
            reverse("partner_dataset_upload"),
            {"data_file": csv_file, "dataset_name": "Imported Finance Data"}
        )

        dataset = InvestorDatasetImport.objects.filter(investor=self.investor).first()
        dataset.status = "imported"
        dataset.save(update_fields=["status"])

        response = self.client.post(
            reverse("confirm_dataset_domain_classification"),
            {
                "dataset_id": dataset.id,
                "confirmed_domain": "finance",
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["confirmed_domain"], "finance")

        dataset.refresh_from_db()
        self.assertEqual(dataset.confirmed_domain, "finance")
    
    def test_confirm_domain_invalid_choice(self):
        """Test that invalid domain choices are rejected."""
        self.client.force_login(self.investor)
        
        csv_data = "data\ntest"
        csv_file = SimpleUploadedFile("test.csv", csv_data.encode(), content_type="text/csv")
        response = self.client.post(
            reverse("partner_dataset_upload"),
            {"data_file": csv_file, "dataset_name": "Test Data"}
        )
        
        dataset = InvestorDatasetImport.objects.filter(investor=self.investor).first()
        
        response = self.client.post(
            reverse("confirm_dataset_domain_classification"),
            {
                "dataset_id": dataset.id,
                "confirmed_domain": "invalid_domain",
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("Invalid domain", data["error"])
    
    def test_confirm_domain_requires_login(self):
        """Test that domain confirmation requires authentication."""
        response = self.client.post(
            reverse("confirm_dataset_domain_classification"),
            {
                "dataset_id": 999,
                "confirmed_domain": "agriculture",
            }
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn("/login", response.url)
    
    def test_confirm_domain_dataset_not_found(self):
        """Test that confirming domain for non-existent dataset returns 404."""
        self.client.force_login(self.investor)
        
        response = self.client.post(
            reverse("confirm_dataset_domain_classification"),
            {
                "dataset_id": 999999,
                "confirmed_domain": "agriculture",
            }
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["ok"])


