# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0005_auto_20150929_1033'),
    ]

    operations = [
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('email_address', models.EmailField(max_length=254, null=True)),
                ('phone_number', models.CharField(max_length=255, null=True)),
                ('facility_code', models.CharField(max_length=255, null=True)),
                ('role', models.CharField(max_length=255, null=True, choices=[(b'EHP', b'EHP'), (b'MANAGER_DISTRICT', b'District Manager'), (b'MANAGER_PROVINCIAL', b'Provincial Manager'), (b'MANAGER_NATIONAL', b'National Manager')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.DeleteModel(
            name='EHP',
        ),
    ]
