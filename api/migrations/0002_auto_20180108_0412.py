# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-08 04:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='matches',
            name='team',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='matches',
            name='won',
            field=models.BooleanField(default=False),
        ),
    ]