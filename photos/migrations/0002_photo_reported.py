# Generated by Django 5.2.3 on 2025-06-15 09:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("photos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="photo",
            name="reported",
            field=models.BooleanField(default=False),
        ),
    ]
