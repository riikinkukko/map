# Generated by Django 3.2.16 on 2025-05-07 14:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('photos', '0003_photo_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('avatar', models.ImageField(default='avatars/default_avatar.png', upload_to='avatars/')),
                ('real_name', models.CharField(blank=True, max_length=100)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('gender', models.CharField(blank=True, choices=[('', 'Не указан'), ('M', 'Мужчина'), ('F', 'Женщина')], max_length=1)),
                ('location', models.CharField(blank=True, max_length=100)),
                ('activity', models.CharField(blank=True, max_length=100)),
                ('website', models.URLField(blank=True)),
                ('about', models.TextField(blank=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
