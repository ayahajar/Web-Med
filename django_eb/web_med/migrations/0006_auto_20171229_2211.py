# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-12-29 22:11
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web_med', '0005_photopng'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='photopng',
            options={'verbose_name': 'photopng', 'verbose_name_plural': 'photospng'},
        ),
    ]
