from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settingspanel', '0004_alter_appsettings_mail_secure'),
    ]

    operations = [
        migrations.AddField(
            model_name='appsettings',
            name='ntfy_server_url',
            field=models.URLField(blank=True, null=True, help_text='Base URL of ntfy server, e.g. https://ntfy.sh'),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='ntfy_topic_default',
            field=models.CharField(max_length=200, blank=True, null=True, help_text="Default topic if user hasn't set one"),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='ntfy_user',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='ntfy_password',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='ntfy_token',
            field=models.CharField(max_length=255, blank=True, null=True, help_text='Bearer token, alternative to user/password'),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='apprise_default_url',
            field=models.TextField(blank=True, null=True, help_text='Apprise URL(s). Multiple allowed, one per line.'),
        ),
    ]
