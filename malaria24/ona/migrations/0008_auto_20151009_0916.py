# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0007_auto_20151009_0817'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportedcase',
            name='facility_code',
            field=models.CharField(max_length=255, blank=True),
        ),
    ]
