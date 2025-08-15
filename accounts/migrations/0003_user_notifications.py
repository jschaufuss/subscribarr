from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_jellyfin_server_user_jellyfin_token_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='notification_channel',
            field=models.CharField(choices=[('email', 'Email'), ('ntfy', 'ntfy'), ('apprise', 'Apprise')], default='email', max_length=10),
        ),
        migrations.AddField(
            model_name='user',
            name='ntfy_topic',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='apprise_url',
            field=models.TextField(blank=True, null=True),
        ),
    ]
