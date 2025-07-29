from django.contrib import admin
from .models import *

admin.site.register(Photo)
admin.site.register(Tag)
admin.site.register(Profile)
admin.site.register(LoginAttempt)
admin.site.register(TagMergeRequest)
admin.site.register(TagGroup)
