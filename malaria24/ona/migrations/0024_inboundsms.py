# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0023_actor_district'),
    ]

    operations = [
        migrations.CreateModel(
            name='InboundSMS',
            fields=[
                ('message_id', models.UUIDField(serialize=False, primary_key=True)),
                ('sender', models.CharField(max_length=255)),
                ('content', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(verbose_name=b'sent at')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reply_to', models.ForeignKey(to='ona.SMS', null=True, on_delete=models.CASCADE)),
            ],
        ),
    ]
