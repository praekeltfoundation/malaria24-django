# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0026_auto_20160203_0818'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actor',
            name='district',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
