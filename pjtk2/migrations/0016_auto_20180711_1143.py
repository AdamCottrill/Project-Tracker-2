# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-07-11 15:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0015_auto_20180710_1145'),
    ]

    operations = [
        migrations.CreateModel(
            name='FundingSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('funding', models.CharField(choices=[('coa', 'COA'), ('spa', 'SPA'), ('other', 'other')], default='spa', max_length=30, verbose_name='Funding Source')),
                ('odoe', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=8, null=True, verbose_name='ODOE')),
                ('salary', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=8, null=True, verbose_name='Salary')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funding_source', to='pjtk2.Project')),
            ],
            options={
                'verbose_name': 'Funding Source',
            },
        ),
        migrations.AlterField(
            model_name='employee',
            name='role',
            field=models.CharField(choices=[('employee', 'Employee'), ('manager', 'Manager'), ('dba', 'DBA')], db_index=True, default='Employee', max_length=30),
        ),
        migrations.AlterField(
            model_name='milestone',
            name='category',
            field=models.CharField(choices=[('Suggested', 'suggested'), ('Core', 'core'), ('Custom', 'custom')], default='Custom', max_length=30),
        ),
    ]
