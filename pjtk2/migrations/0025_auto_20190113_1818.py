# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-01-13 23:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0024_auto_20190113_1724'),
    ]

    operations = [
        migrations.AlterField(
            model_name='milestone',
            name='category',
            field=models.CharField(choices=[('Custom', 'custom'), ('Suggested', 'suggested'), ('Core', 'core')], default='Custom', max_length=30),
        ),
    ]
