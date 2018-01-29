# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-13 00:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_auto_20180111_0208'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserLeagues',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('region', models.CharField(max_length=10)),
                ('queue', models.CharField(max_length=30)),
                ('tier', models.CharField(max_length=20)),
                ('division', models.CharField(max_length=10)),
                ('points', models.IntegerField(default=0)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='userleagues',
            unique_together=set([('user_id', 'region', 'queue')]),
        ),
    ]