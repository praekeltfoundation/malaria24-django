# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0011_auto_20151009_1018'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='facility',
            options={'verbose_name': 'Facility', 'verbose_name_plural': 'Facilities'},
        ),
        migrations.AddField(
            model_name='reportedcase',
            name='landmark_description',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
