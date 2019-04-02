# Generated by Django 2.1.7 on 2019-03-27 09:59

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0012_customer_sale'),
    ]

    operations = [
        migrations.AddField(
            model_name='sku',
            name='run_cost',
            field=models.DecimalField(decimal_places=6, default=1.0, help_text='The cost per case to manufacture SKU separate from ingredient cost', max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=1e-06, message='The manufacturing rate must be positive.')], verbose_name='Manufacturing Run Cost'),
        ),
        migrations.AddField(
            model_name='sku',
            name='setup_cost',
            field=models.DecimalField(decimal_places=6, default=1.0, help_text='The fixed retooling cost to prepare a manufacturing line', max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=1e-06, message='The manufacturing rate must be positive.')], verbose_name='Manufacturing Setup Cost'),
        ),
    ]