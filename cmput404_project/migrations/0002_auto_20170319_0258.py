# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-19 02:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cmput404_project', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Friend',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requestee', models.URLField()),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='follow', to='cmput404_project.Author')),
            ],
        ),
        migrations.CreateModel(
            name='Notify',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requester', models.URLField()),
                ('requestee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notify', to='cmput404_project.Author')),
            ],
        ),
        migrations.CreateModel(
            name='VisibileTo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visibileTo', models.URLField()),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visibileTo', to='cmput404_project.Author')),
            ],
        ),
        migrations.AlterField(
            model_name='category',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='cmput404_project.Post'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='cmput404_project.Post'),
        ),
    ]