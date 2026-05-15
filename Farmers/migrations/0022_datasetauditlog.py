from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Farmers", "0021_userprofile_dashboard_layout"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatasetAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("upload_preview", "Upload Preview"),
                            ("import", "Import"),
                            ("discard", "Discard"),
                            ("delete", "Delete"),
                            ("load_existing", "Load Existing"),
                            ("save_layout", "Save Layout"),
                        ],
                        max_length=40,
                    ),
                ),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dataset_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dataset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="Farmers.investordatasetimport",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="datasetauditlog",
            index=models.Index(fields=["actor", "created_at"], name="Farmers_dat_actor_i_32cc17_idx"),
        ),
        migrations.AddIndex(
            model_name="datasetauditlog",
            index=models.Index(fields=["action", "created_at"], name="Farmers_dat_action__00d260_idx"),
        ),
    ]
