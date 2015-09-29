# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0004_sms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportedcase',
            name='landmark',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='reportedcase',
            name='sa_id_number',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
