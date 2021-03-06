# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-12-29 15:41
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('web_med', '0003_auto_20171128_0402'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='photo',
            name='title',
        ),
        migrations.RemoveField(
            model_name='photo',
            name='uploaded_at',
        ),
        migrations.AlterField(
            model_name='photo',
            name='patient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_photos', to='web_med.Patient'),
        ),
    ]
