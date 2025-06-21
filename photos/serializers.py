from rest_framework import serializers
from .models import Photo, Tag


class PhotoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Photo
        fields = ['id', 'image', 'description', 'date_taken', 'latitude', 'longitude', 'name', 'tag']

