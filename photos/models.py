from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth import get_user_model
import os
from django.core.validators import FileExtensionValidator
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.utils import timezone
from datetime import timedelta


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Photo(models.Model):
    name = models.TextField(null=True)
    image = models.ImageField(upload_to='photos/')
    description = models.TextField()
    date_taken = models.DateField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name='photos')
    REPORTED_CHOICES = [
        ('law', 'Нарушение законодательства РФ'),
        ('ai', 'Фото — генерация нейросети'),
        ('rules', 'Нарушение правил сайта'),
    ]
    reported = models.BooleanField(default=False)
    reported_at = models.CharField(max_length=10, choices=REPORTED_CHOICES, default='law')
    add_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_DEFAULT,
        default=1,
        related_name='photos_added'
    )

    def __str__(self):
        return f"Photo taken on {self.date_taken} at ({self.latitude}, {self.longitude})"

    def compress_image(self, image):
        # сжимаем фото если больше 2мб
        img = Image.open(image)

        # Если изображение весит больше 2MB (2 * 1024 * 1024 bytes)
        if image.size > 2 * 1024 * 1024:
            output = BytesIO()

            # Конвертируем в RGB если это PNG с прозрачностью
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Сохраняем с качеством 50%
            img.save(output, format='JPEG', quality=50)
            output.seek(0)

            # Создаем новый InMemoryUploadedFile
            compressed_image = InMemoryUploadedFile(
                output,
                'ImageField',
                f"{image.name.split('.')[0]}.jpg",
                'image/jpeg',
                sys.getsizeof(output),
                None
            )
            return compressed_image
        return image

    def save(self, *args, **kwargs):
        # Сжимаем новое фото если нужно
        if self.image and hasattr(self.image, 'file'):
            self.image = self.compress_image(self.image)

        super().save(*args, **kwargs)


class Profile(models.Model):
    GENDER_CHOICES = [
        ('', 'Не указан'),
        ('M', 'Мужчина'),
        ('F', 'Женщина'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(
        upload_to='avatars/',
        default='avatars/default_avatar.png',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    real_name = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    location = models.CharField(max_length=100, blank=True)
    activity = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    about = models.TextField(blank=True)

    def __str__(self):
        return f'Профиль {self.user.username}'

    def compress_avatar(self, avatar):
        # сжимаем фото если больше 2мб
        img = Image.open(avatar)

        if avatar.size > 2 * 1024 * 1024:
            output = BytesIO()
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=50)
            output.seek(0)
            compressed_avatar = InMemoryUploadedFile(
                output,
                'ImageField',
                f"{avatar.name.split('.')[0]}.jpg",
                'image/jpeg',
                sys.getsizeof(output),
                None
            )
            return compressed_avatar
        return avatar

    def save(self, *args, **kwargs):
        # Сжимаем новую аватарку если нужно
        if self.avatar and self.avatar.name != 'avatars/default_avatar.png':
            if hasattr(self.avatar, 'file'):
                self.avatar = self.compress_avatar(self.avatar)

        # Удаляем старый аватар при обновлении
        try:
            old_profile = Profile.objects.get(pk=self.pk)
            if old_profile.avatar and old_profile.avatar != self.avatar:
                if old_profile.avatar.name != 'avatars/default_avatar.png':
                    old_path = old_profile.avatar.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
        except Profile.DoesNotExist:
            pass

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.avatar.name != 'avatars/default_avatar.png':
            if os.path.exists(self.avatar.path):
                os.remove(self.avatar.path)
        super().delete(*args, **kwargs)

class Comment(models.Model):
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField("Комментарий")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Комментарий от {self.user.username} к {self.photo.id}'


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    blocked_until = models.DateTimeField(null=True, blank=True)

    def is_blocked(self):
        return self.blocked_until and self.blocked_until > timezone.now()

    def reset_attempts(self):
        self.attempts = 0
        self.blocked_until = None
        self.save()


class TagMergeRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('accepted', 'Принят'),
        ('declined', 'Отклонен'),
    ]

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='merge_requests')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tag_merge_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tag_merge_received')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        unique_together = ('tag', 'from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} → {self.to_user} по тегу '{self.tag.name}' ({self.status})"


class TagGroup(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='groups')
    members = models.ManyToManyField(User, related_name='tag_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Группа по тегу '{self.tag.name}'"

