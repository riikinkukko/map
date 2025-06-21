from django import forms
from .models import Photo, Profile, Comment
from django.contrib.auth.models import User

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Подтвердите пароль')
    accept_terms = forms.BooleanField(label='Я принимаю условия', required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Пароли не совпадают.")
        return cleaned_data


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['name', 'image', 'description', 'date_taken', 'latitude', 'longitude']

        widgets = {
            'date_taken': forms.DateInput(attrs={'type': 'date'}),
            'latitude' : forms.NumberInput(attrs={'id': 'field1'}),
            'longitude': forms.NumberInput(attrs={'id': 'field2'}),
        }

class PhotoEditForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['name', 'image', 'description', 'date_taken', 'latitude', 'longitude']
        widgets = {
            'date_taken': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'  # 💡 Ключевая строка
            ),
            'description': forms.Textarea(attrs={'rows': 4}),
            'latitude': forms.NumberInput(attrs={'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'step': 'any'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.date_taken:
            self.initial['date_taken'] = self.instance.date_taken.strftime('%Y-%m-%d')

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'avatar',
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

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Оставьте комментарий...'})
        }

class PhotoReportForm(forms.Form):
    reason = forms.ChoiceField(
        choices=Photo.REPORTED_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )