# Generated by Django 2.1.5 on 2019-01-27 21:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0005_merge_20190127_1649'),
    ]

    operations = [
        migrations.AddField(
            model_name='manufacturegoal',
            name='form_name',
            field=models.CharField(default='Morton', max_length=100),
        ),
    ]
