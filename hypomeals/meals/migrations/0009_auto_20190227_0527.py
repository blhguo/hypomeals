# Generated by Django 2.1.7 on 2019-02-27 10:27

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0008_auto_20190226_0323'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formulaingredient',
            name='quantity',
            field=models.DecimalField(decimal_places=6, max_digits=20),
        ),
        migrations.AlterField(
            model_name='goalitem',
            name='quantity',
            field=models.DecimalField(decimal_places=6, max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=1e-06, message='Quantity must be positive')], verbose_name='Quantity'),
        ),
        migrations.AlterField(
            model_name='ingredient',
            name='cost',
            field=models.DecimalField(decimal_places=2, max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=0.01, message='Cost must be positive.')], verbose_name='Cost'),
        ),
        migrations.AlterField(
            model_name='ingredient',
            name='size',
            field=models.DecimalField(decimal_places=6, max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=1e-06, message='Size of ingredient must be positive.')], verbose_name='Size'),
        ),
        migrations.AlterField(
            model_name='sku',
            name='formula_scale',
            field=models.DecimalField(decimal_places=6, default=1.0, max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=1e-06, message='The formula scale factor must be positive.')], verbose_name='Formula Scale Factor'),
        ),
        migrations.AlterField(
            model_name='sku',
            name='manufacturing_rate',
            field=models.DecimalField(decimal_places=6, default=1.0, help_text='Manufacturing rate for this SKU in cases per hour', max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=1e-06, message='The manufacturing rate must be positive.')], verbose_name='Manufacturing Rate'),
        ),
        migrations.AlterField(
            model_name='unit',
            name='scale_factor',
            field=models.DecimalField(decimal_places=6, max_digits=20, validators=[django.core.validators.MinValueValidator(limit_value=1e-06, message='Unit scale factor must be positive.')]),
        ),
    ]
