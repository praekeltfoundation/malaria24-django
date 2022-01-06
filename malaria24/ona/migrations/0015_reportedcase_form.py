# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0014_onaform'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportedcase',
            name='form',
            field=models.ForeignKey(blank=True, to='ona.OnaForm', null=True, on_delete=models.CASCADE),
        ),
    ]
