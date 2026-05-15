from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Farmers", "0020_investordatasetimport_investordatasetrow"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="dashboard_layout",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
