# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0010_auto_20151009_1005'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='created_at',
            field=models.DateTimeField(default=timezone.now(), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='facility',
            name='updated_at',
            field=models.DateTimeField(default=timezone.now(), auto_now=True),
            preserve_default=False,
        ),
    ]
