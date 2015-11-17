# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0015_reportedcase_form'),
    ]

    operations = [
        migrations.AddField(
            model_name='actor',
            name='province',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'EC', b'The Eastern Cape'), (b'FS', b'The Free State'), (b'GP', b'Gauteng'), (b'KZN', b'KwaZulu-Natal'), (b'LP', b'Limpopo'), (b'MP', b'Mpumalanga'), (b'NC', b'The Northern Cape'), (b'NW', b'North West'), (b'WC)', b'The Western Cape')]),
        ),
    ]
