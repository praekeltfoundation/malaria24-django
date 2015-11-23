# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0016_actor_province'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actor',
            name='province',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'The Eastern Cape', b'The Eastern Cape'), (b'The Free State', b'The Free State'), (b'Gauteng', b'Gauteng'), (b'KwaZulu-Natal', b'KwaZulu-Natal'), (b'Limpopo', b'Limpopo'), (b'Mpumalanga', b'Mpumalanga'), (b'The Northern Cape', b'The Northern Cape'), (b'North West', b'North West'), (b'The Western Cape', b'The Western Cape')]),
        ),
        migrations.AlterField(
            model_name='actor',
            name='role',
            field=models.CharField(max_length=255, null=True, choices=[(b'EHP', b'EHP'), (b'CASE_INVESTIGATOR', b'Case Investigator'), (b'MANAGER_DISTRICT', b'District Manager'), (b'MANAGER_PROVINCIAL', b'Provincial Manager'), (b'MANAGER_NATIONAL', b'National Manager'), (b'MIS', b'MIS')]),
        ),
        migrations.AlterField(
            model_name='facility',
            name='province',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'The Eastern Cape', b'The Eastern Cape'), (b'The Free State', b'The Free State'), (b'Gauteng', b'Gauteng'), (b'KwaZulu-Natal', b'KwaZulu-Natal'), (b'Limpopo', b'Limpopo'), (b'Mpumalanga', b'Mpumalanga'), (b'The Northern Cape', b'The Northern Cape'), (b'North West', b'North West'), (b'The Western Cape', b'The Western Cape')]),
        ),
    ]
