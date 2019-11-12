# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0026_reportedcase_jembi_alert_sent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportedcase',
            name='jembi_alert_sent',
            field=models.BooleanField(default=False),
        ),
    ]
