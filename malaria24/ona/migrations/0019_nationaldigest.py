# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0018_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='NationalDigest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipients', models.ManyToManyField(to='ona.Actor')),
            ],
        ),
    ]
