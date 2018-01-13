# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-13 01:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_auto_20180113_0009'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserChampionMasteries',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('region', models.CharField(max_length=10)),
                ('champ_id', models.IntegerField()),
                ('level', models.IntegerField(default=0)),
                ('total_points', models.IntegerField(default=0)),
                ('points_since_last', models.IntegerField(default=0)),
                ('points_to_next', models.IntegerField(default=0)),
                ('chest_granted', models.BooleanField(default=False)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='userchampionmasteries',
            unique_together=set([('user_id', 'region', 'champ_id')]),
        ),
    ]
