from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settingspanel", "0007_appsettings_notify_lookahead_days"),
    ]

    operations = [
        migrations.AddField(
            model_name="appsettings",
            name="youtube_enabled",
            field=models.BooleanField(default=True, help_text="Enable the YouTube subscription feature globally (navigation + routes)."),
        ),
    ]
