# Generated by Django 3.2.12 on 2022-10-07 19:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0005_auto_20221005_0941'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectimage',
            name='alt_text',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='alternative text for screen readers'),
        ),
    ]