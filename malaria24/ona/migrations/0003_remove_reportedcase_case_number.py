# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0002_reportedcase_case_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportedcase',
            name='case_number',
        ),
    ]
