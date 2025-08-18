from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settingspanel', '0005_appsettings_notifications'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArrInstance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('sonarr', 'Sonarr'), ('radarr', 'Radarr')], max_length=10)),
                ('name', models.CharField(help_text='Friendly name, e.g. Home, 4K, Anime', max_length=100)),
                ('base_url', models.URLField()),
                ('api_key', models.CharField(max_length=255)),
                ('enabled', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0, help_text='Sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['order', 'id'],
                'unique_together': {('kind', 'name')},
            },
        ),
    ]
