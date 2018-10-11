# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-07-12 18:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0018_auto_20180712_1202'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='funding',
        ),
        migrations.RemoveField(
            model_name='project',
            name='odoe',
        ),
        migrations.RemoveField(
            model_name='project',
            name='salary',
        ),
        migrations.AlterField(
            model_name='employee',
            name='role',
            field=models.CharField(choices=[('employee', 'Employee'), ('dba', 'DBA'), ('manager', 'Manager')], db_index=True, default='Employee', max_length=30),
        ),
        migrations.AlterField(
            model_name='message',
            name='level',
            field=models.CharField(choices=[('info', 'Info'), ('actionrequired', 'Action Required')], default='info', max_length=30),
        ),
        migrations.AlterField(
            model_name='milestone',
            name='category',
            field=models.CharField(choices=[('Suggested', 'suggested'), ('Custom', 'custom'), ('Core', 'core')], default='Custom', max_length=30),
        ),
    ]