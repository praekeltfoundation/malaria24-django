# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0025_smsevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportedcase',
            name='jembi_alert_sent',
            field=models.BooleanField(default=True),
        ),
    ]
