# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0009_auto_20151009_0919'),
    ]

    operations = [
        migrations.CreateModel(
            name='Facility',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('facility_code', models.CharField(max_length=255)),
                ('facility_name', models.CharField(max_length=255, null=True, blank=True)),
                ('district', models.CharField(max_length=255, null=True, blank=True)),
                ('subdistrict', models.CharField(max_length=255, null=True, blank=True)),
                ('phase', models.CharField(max_length=255, null=True, blank=True)),
                ('province', models.CharField(max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.AlterField(
            model_name='reportedcase',
            name='digest',
            field=models.ForeignKey(blank=True, to='ona.Digest', null=True, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='reportedcase',
            name='ehps',
            field=models.ManyToManyField(to='ona.Actor', blank=True),
        ),
    ]
