# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-04 04:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_auto_20171127_1029'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChampionItems',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('champ_id', models.IntegerField()),
                ('item_id', models.IntegerField()),
                ('occurence', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='ChampionRunes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('champ_id', models.IntegerField()),
                ('rune_id', models.IntegerField()),
                ('occurence', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='ChampionStats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('champ_id', models.IntegerField()),
                ('total_games', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='matches',
            name='gold',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='matches',
            name='lane',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profilestats',
            name='time_played',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='assists',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='cs',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='deaths',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='duration',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='item0',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='item1',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='item2',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='item3',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='item4',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='item5',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='item6',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='kills',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='level',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='season_id',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='spell0',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='spell1',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='timestamp',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='vision_wards_bought',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='wards_killed',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='matches',
            name='wards_placed',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='profilestats',
            name='last_match_updated',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='profilestats',
            name='last_updated',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterUniqueTogether(
            name='championrunes',
            unique_together=set([('champ_id', 'rune_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='championitems',
            unique_together=set([('champ_id', 'item_id')]),
        ),
    ]
