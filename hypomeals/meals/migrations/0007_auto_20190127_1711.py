# Generated by Django 2.1.5 on 2019-01-27 22:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0006_manufacturegoal_form_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='manufacturegoal',
            name='save_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='manufacturegoal',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
    ]
