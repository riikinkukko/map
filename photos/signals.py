import os
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth.models import User
from .models import Profile, Photo

# Существующий код для создания профиля
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

# Перенос файлов при удалении (Удаляются из БД)
def move_to_deleted_folder(file_path):
    # Переносит файл в папку deleted_photos, сохраняя оригинальное имя
    if not file_path:  # Проверка на пустой путь
        return False

    original_path = os.path.join(settings.MEDIA_ROOT, file_path)
    if not os.path.exists(original_path):  # Если файл уже перемещен/удален
        return False

    # Создаем папку deleted_photos (если её нет)
    deleted_dir = os.path.join(settings.MEDIA_ROOT, 'deleted_photos')
    os.makedirs(deleted_dir, exist_ok=True)

    # Новый путь: media/deleted_photos/оригинальное_имя_файла
    new_path = os.path.join('deleted_photos', os.path.basename(file_path))
    full_new_path = os.path.join(settings.MEDIA_ROOT, new_path)

    # Уникальное имя, если файл уже существует в deleted_photos
    counter = 1
    while os.path.exists(full_new_path):
        name, ext = os.path.splitext(os.path.basename(file_path))
        full_new_path = os.path.join(
            settings.MEDIA_ROOT,
            'deleted_photos',
            f"{name}_{counter}{ext}"
        )
        counter += 1

    os.rename(original_path, full_new_path)
    return True

@receiver(pre_delete, sender=Photo)
def move_photo_on_delete(sender, instance, **kwargs):
    if instance.image:
        move_to_deleted_folder(instance.image.name)

@receiver(pre_delete, sender=Profile)
def move_avatar_on_delete(sender, instance, **kwargs):
    # Не трогаем дефолтный аватар
    if instance.avatar and instance.avatar.name != 'avatars/default_avatar.jpg':
        move_to_deleted_folder(instance.avatar.name)
