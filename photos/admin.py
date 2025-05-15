from django.contrib import admin
from .models import Photo, Tag, Profile
# Register your models here.
admin.site.register(Photo)
admin.site.register(Tag)
admin.site.register(Profile)