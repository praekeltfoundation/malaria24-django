# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-12-22 11:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0027_auto_20191101_1137'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actor',
            name='province',
            field=models.CharField(blank=True, choices=[('The Eastern Cape', 'The Eastern Cape'), ('The Free State', 'The Free State'), ('Gauteng', 'Gauteng'), ('KwaZulu-Natal', 'KwaZulu-Natal'), ('Limpopo', 'Limpopo'), ('Mpumalanga', 'Mpumalanga'), ('The Northern Cape', 'The Northern Cape'), ('North West', 'North West'), ('The Western Cape', 'The Western Cape')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='actor',
            name='role',
            field=models.CharField(choices=[('EHP', 'EHP'), ('CASE_INVESTIGATOR', 'Case Investigator'), ('MANAGER_DISTRICT', 'District Manager'), ('MANAGER_PROVINCIAL', 'Provincial Manager'), ('MANAGER_NATIONAL', 'National Manager'), ('MIS', 'MIS')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='facility',
            name='province',
            field=models.CharField(blank=True, choices=[('The Eastern Cape', 'The Eastern Cape'), ('The Free State', 'The Free State'), ('Gauteng', 'Gauteng'), ('KwaZulu-Natal', 'KwaZulu-Natal'), ('Limpopo', 'Limpopo'), ('Mpumalanga', 'Mpumalanga'), ('The Northern Cape', 'The Northern Cape'), ('North West', 'North West'), ('The Western Cape', 'The Western Cape')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='inboundsms',
            name='timestamp',
            field=models.DateTimeField(verbose_name='sent at'),
        ),
    ]
