# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0021_districtdigest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportedcase',
            name='case_number',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='reportedcase',
            name='landmark_description',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
