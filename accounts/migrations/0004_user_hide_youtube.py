from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_notifications"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="hide_youtube",
            field=models.BooleanField(default=False, help_text="Hide YouTube feature in navigation for this user only."),
        ),
    ]
