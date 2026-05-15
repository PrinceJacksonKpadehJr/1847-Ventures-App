from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Farmers", "0024_investordatasetimport_column_metadata_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="investordatasetimport",
            name="file_format",
            field=models.CharField(
                choices=[("csv", "CSV"), ("xlsx", "XLSX"), ("json", "JSON")],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="datasetauditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("upload_preview", "Upload Preview"),
                    ("api_ingest", "API Ingest"),
                    ("incremental_upload", "Incremental Upload"),
                    ("import", "Import"),
                    ("discard", "Discard"),
                    ("delete", "Delete"),
                    ("load_existing", "Load Existing"),
                    ("save_layout", "Save Layout"),
                ],
                max_length=40,
            ),
        ),
    ]
