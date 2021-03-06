# Generated by Django 2.2.11 on 2020-06-02 20:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pjtk2', '0002_fulltextsearch_trigger'),
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
            field=models.CharField(choices=[('actionrequired', 'Action Required'), ('info', 'Info')], default='info', max_length=30),
        ),
        migrations.AlterField(
            model_name='milestone',
            name='category',
            field=models.CharField(choices=[('Suggested', 'suggested'), ('Core', 'core'), ('Custom', 'custom')], default='Custom', max_length=30),
        ),
    ]
