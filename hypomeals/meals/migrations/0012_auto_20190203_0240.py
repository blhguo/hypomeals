# Generated by Django 2.1.5 on 2019-02-03 07:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0011_auto_20190203_0222'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sku',
            name='name',
            field=models.CharField(max_length=32, unique=True),
        ),
    ]
