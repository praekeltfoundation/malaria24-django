# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0012_auto_20151014_1953'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportedcase',
            name='case_number',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
