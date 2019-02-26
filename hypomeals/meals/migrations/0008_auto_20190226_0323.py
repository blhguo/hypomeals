# Generated by Django 2.1.7 on 2019-02-26 08:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0007_auto_20190226_0536'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='goal',
            options={'ordering': ['-save_time']},
        ),
        migrations.AddField(
            model_name='formulaingredient',
            name='unit',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='meals.Unit'),
            preserve_default=False,
        ),
    ]