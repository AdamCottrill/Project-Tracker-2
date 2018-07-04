# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-29 14:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0010_auto_20180629_1024'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='role',
            field=models.CharField(choices=[('dba', 'DBA'), ('manager', 'Manager'), ('employee', 'Employee')], db_index=True, default='Employee', max_length=30),
        ),
        migrations.AlterField(
            model_name='messages2users',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='messages2users',
            name='read',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='milestone',
            name='category',
            field=models.CharField(choices=[('Suggested', 'suggested'), ('Custom', 'custom'), ('Core', 'core')], default='Custom', max_length=30),
        ),
        migrations.AlterField(
            model_name='project',
            name='funding',
            field=models.CharField(choices=[('other', 'other'), ('coa', 'COA'), ('spa', 'SPA')], default='spa', max_length=30, verbose_name='Funding Source'),
        ),
        migrations.AlterField(
            model_name='projectmilestones',
            name='completed',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='projectmilestones',
            name='required',
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]