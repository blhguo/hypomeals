# Generated by Django 2.1.5 on 2019-01-28 19:27

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0007_auto_20190127_1711'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manufacturegoal',
            name='save_time',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now),
        ),
    ]