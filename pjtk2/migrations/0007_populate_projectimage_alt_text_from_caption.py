# Generated by Django 3.2.12 on 2022-10-07 19:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0006_add_projectimage_alt_text'),
    ]

    operations = [
        migrations.RunSQL(
            "update pjtk2_projectimage set alt_text=caption;",
            "update pjtk2_projectimage set alt_text=NULL;"
      )
    ]
