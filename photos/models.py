from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth import get_user_model


class Photo(models.Model):
    name = models.TextField(null=True)
    image = models.ImageField(upload_to='photos/')
    description = models.TextField()
    date_taken = models.DateField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    tags = models.ManyToManyField('Tag', blank=True)
    add_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_DEFAULT,
        default=1,
        related_name='photos_added'
    )
    def __str__(self):
        return f"Photo taken on {self.date_taken} at ({self.latitude}, {self.longitude})"


class Tag(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name



class Profile(models.Model):
    GENDER_CHOICES = [
        ('', 'Не указан'),
        ('M', 'Мужчина'),
        ('F', 'Женщина'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default_avatar.jpg')
    real_name = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    location = models.CharField(max_length=100, blank=True)
    activity = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    about = models.TextField(blank=True)

    def __str__(self):
        return f'Профиль {self.user.username}'

"""
class Comments(models.Model):
    id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_DEFAULT,
        default=1,
        related_name='comments_added'
    )
    text = models.TextField()
    date = models.DateTimeField()
"""