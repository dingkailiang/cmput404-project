# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-09 21:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cmput404_project', '0003_auto_20170407_2249'),
    ]

    operations = [
        migrations.AlterField(
            model_name='author',
            name='host',
            field=models.URLField(default=b'https://fierce-savannah-93127.herokuapp.com'),
        ),
    ]
