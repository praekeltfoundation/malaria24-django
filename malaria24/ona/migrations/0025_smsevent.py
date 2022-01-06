# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0024_inboundsms'),
    ]

    operations = [
        migrations.CreateModel(
            name='SMSEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event_type', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField()),
                ('sms', models.ForeignKey(to='ona.SMS', on_delete=models.CASCADE)),
            ],
        ),
    ]
