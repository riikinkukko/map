from django import forms
from .models import Photo, Profile

class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['name', 'image', 'description', 'date_taken', 'latitude', 'longitude']

        widgets = {
            'date_taken': forms.DateInput(attrs={'type': 'date'}),
            'latitude' : forms.NumberInput(attrs={'id': 'field1'}),
            'longitude': forms.NumberInput(attrs={'id': 'field2'}),
        }

# forms.py
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'avatar',  # Добавлено!
            'real_name',
            'birth_date',
            'gender',
            'location',
            'activity',
            'website',
            'about',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }
