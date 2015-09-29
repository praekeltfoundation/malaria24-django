# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EHP',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('email_address', models.EmailField(max_length=254, null=True)),
                ('phone_number', models.CharField(max_length=255)),
                ('facility_code', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ReportedCase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('locality', models.CharField(max_length=255)),
                ('date_of_birth', models.CharField(max_length=255)),
                ('create_date_time', models.DateTimeField()),
                ('sa_id_number', models.CharField(max_length=255)),
                ('msisdn', models.CharField(max_length=255)),
                ('id_type', models.CharField(max_length=255)),
                ('abroad', models.CharField(max_length=255)),
                ('reported_by', models.CharField(max_length=255)),
                ('gender', models.CharField(max_length=255)),
                ('facility_code', models.CharField(max_length=255)),
                ('landmark', models.CharField(max_length=255)),
                ('_id', models.CharField(max_length=255)),
                ('_uuid', models.CharField(max_length=255)),
                ('_xform_id_string', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
