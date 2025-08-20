from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('settingspanel', '0006_arr_instance'),
    ]

    operations = [
        migrations.AddField(
            model_name='appsettings',
            name='notify_lookahead_days',
            field=models.PositiveSmallIntegerField(default=1, help_text='How many days ahead to consider for notifications (early availability). Set to 0 or 1 for only today.'),
        ),
    ]
