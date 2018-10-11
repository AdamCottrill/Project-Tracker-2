# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-07-12 13:28
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0016_auto_20180711_1143'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectFunding',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('odoe', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=8, null=True, verbose_name='ODOE')),
                ('salary', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=8, null=True, verbose_name='Salary')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funding_sources', to='pjtk2.Project')),
            ],
        ),
        migrations.RemoveField(
            model_name='fundingsource',
            name='funding',
        ),
        migrations.RemoveField(
            model_name='fundingsource',
            name='odoe',
        ),
        migrations.RemoveField(
            model_name='fundingsource',
            name='project',
        ),
        migrations.RemoveField(
            model_name='fundingsource',
            name='salary',
        ),
        migrations.AddField(
            model_name='fundingsource',
            name='abbrev',
            field=models.CharField(default=1, max_length=25),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fundingsource',
            name='name',
            field=models.CharField(default='foo', max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='projectfunding',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_allocations', to='pjtk2.FundingSource'),
        ),
    ]