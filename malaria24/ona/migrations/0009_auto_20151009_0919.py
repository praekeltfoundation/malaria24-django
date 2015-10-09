# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0008_auto_20151009_0916'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actor',
            name='email_address',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='actor',
            name='facility_code',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='actor',
            name='phone_number',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='reportedcase',
            name='facility_code',
            field=models.CharField(max_length=255),
        ),
    ]
