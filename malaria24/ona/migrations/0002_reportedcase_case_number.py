# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportedcase',
            name='case_number',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
