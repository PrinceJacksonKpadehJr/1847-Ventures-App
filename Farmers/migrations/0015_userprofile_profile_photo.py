from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Farmers", "0014_rebuild_userprofile_fk_to_farmer"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="profile_photo",
            field=models.FileField(blank=True, null=True, upload_to="profile_pictures/"),
        ),
    ]
