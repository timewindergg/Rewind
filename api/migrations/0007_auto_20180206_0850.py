# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-02-06 08:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_matchlawn'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserChampionItems',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('region', models.CharField(max_length=10)),
                ('champ_id', models.IntegerField()),
                ('season_id', models.IntegerField()),
                ('lane', models.CharField(max_length=50)),
                ('item_id', models.IntegerField()),
                ('occurence', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='UserChampionRunes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('region', models.CharField(max_length=10)),
                ('champ_id', models.IntegerField()),
                ('season_id', models.IntegerField()),
                ('lane', models.CharField(max_length=50)),
                ('rune_set', models.TextField()),
                ('occurence', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='UserChampionVersusStats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('region', models.CharField(max_length=10)),
                ('season_id', models.IntegerField()),
                ('champ_id', models.IntegerField()),
                ('enemy_champ_id', models.IntegerField()),
                ('wins', models.IntegerField(default=0)),
                ('losses', models.IntegerField(default=0)),
                ('total_games', models.IntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='userchampionstats',
            name='gold',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userchampionstats',
            name='total_games20',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userchampionstats',
            name='total_games25',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userchampionstats',
            name='total_games30',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userchampionstats',
            name='total_games35',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userchampionstats',
            name='total_games40',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userchampionstats',
            name='total_games40p',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterUniqueTogether(
            name='userchampionversusstats',
            unique_together=set([('user_id', 'region', 'season_id', 'champ_id', 'enemy_champ_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='userchampionrunes',
            unique_together=set([('user_id', 'region', 'season_id', 'champ_id', 'lane')]),
        ),
        migrations.AlterUniqueTogether(
            name='userchampionitems',
            unique_together=set([('user_id', 'region', 'season_id', 'champ_id', 'lane', 'item_id')]),
        ),
    ]