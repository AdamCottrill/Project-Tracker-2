# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-29 14:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0011_auto_20180629_1031'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='role',
            field=models.CharField(choices=[('manager', 'Manager'), ('dba', 'DBA'), ('employee', 'Employee')], db_index=True, default='Employee', max_length=30),
        ),
        migrations.AlterField(
            model_name='message',
            name='level',
            field=models.CharField(choices=[('info', 'Info'), ('actionrequired', 'Action Required')], default='info', max_length=30),
        ),
        migrations.AlterField(
            model_name='milestone',
            name='category',
            field=models.CharField(choices=[('Core', 'core'), ('Custom', 'custom'), ('Suggested', 'suggested')], default='Custom', max_length=30),
        ),
        migrations.AlterField(
            model_name='project',
            name='funding',
            field=models.CharField(choices=[('coa', 'COA'), ('other', 'other'), ('spa', 'SPA')], default='spa', max_length=30, verbose_name='Funding Source'),
        ),
    ]
