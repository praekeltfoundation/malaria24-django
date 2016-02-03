# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ona', '0025_auto_20160203_0817'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actor',
            name='district',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[('Amajuba', 'Amajuba'), ('Capricorn', 'Capricorn'), ('Ehlanzeni', 'Ehlanzeni'), ('Gert Sibande', 'Gert Sibande'), ('Greater Sekhukhune', 'Greater Sekhukhune'), ('Harry Gwala', 'Harry Gwala'), ('Mopani', 'Mopani'), ('Nkangala', 'Nkangala'), ('Ugu', 'Ugu'), ('Umkhanyakude', 'Umkhanyakude'), ('Umzinyathi', 'Umzinyathi'), ('Uthukela', 'Uthukela'), ('Uthungulu', 'Uthungulu'), ('Vhembe', 'Vhembe'), ('Waterberg', 'Waterberg'), ('Zululand', 'Zululand'), ('eThekwini Metropolitan Municipality', 'eThekwini Metropolitan Municipality'), ('iLembe', 'iLembe'), ('uMgungundlovu', 'uMgungundlovu')]),
        ),
    ]
