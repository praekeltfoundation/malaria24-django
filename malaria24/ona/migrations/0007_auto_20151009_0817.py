# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0006_auto_20150929_1205'),
    ]

    operations = [
        migrations.CreateModel(
            name='Digest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipients', models.ManyToManyField(to='ona.Actor')),
            ],
        ),
        migrations.AddField(
            model_name='reportedcase',
            name='ehps',
            field=models.ManyToManyField(to='ona.Actor'),
        ),
        migrations.AddField(
            model_name='reportedcase',
            name='digest',
            field=models.ForeignKey(to='ona.Digest', null=True, on_delete=models.CASCADE),
        ),
    ]
