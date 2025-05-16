from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import status
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import PhotoSerializer
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from .models import Profile
from .forms import ProfileForm
from .models import Photo, Tag
from .forms import PhotoForm
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify


@login_required
def upload_photo(request):
    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.add_id = request.user
            photo.save()
            form.save_m2m()
            return redirect('map')
    else:
        form = PhotoForm()
    return render(request, 'photos/upload.html', {'form': form})

class MapView(TemplateView):
    template_name = 'photos/map.html'

class PhotoView(APIView):
    def get(self, request, *args, **kwargs):
        xmin = request.GET.get('xmin')
        ymin = request.GET.get('ymin')
        xmax = request.GET.get('xmax')
        ymax = request.GET.get('ymax')

        # Проверка на отсутствие параметров
        if not (xmin and ymin and xmax and ymax):
            return Response({"error": "Missing required parameters."}, status=400)

        try:
            xmin = float(xmin)
            ymin = float(ymin)
            xmax = float(xmax)
            ymax = float(ymax)
        except ValueError:
            return Response({"error": "Invalid coordinate values."}, status=400)

        # Получаем фотографии в указанной области
        photos = Photo.objects.filter(
            latitude__gte=ymin, latitude__lte=ymax,
            longitude__gte=xmin, longitude__lte=xmax
        )

        # Сериализация данных фотографий
        serializer = PhotoSerializer(photos, many=True)
        return Response(serializer.data)

def view_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)

    return render(request, 'photos/photo.html', {
        'photo': photo,
    })


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь уже существует')
            return redirect('register')
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('/')  # На главную
    return render(request, 'accounts/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        messages.error(request, 'Неверный логин или пароль')
        return redirect('login')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('/')


class PhotoGeoJSONView(APIView):
    def get(self, request, *args, **kwargs):
        photos = Photo.objects.all()

        features = []
        for photo in photos:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [photo.longitude, photo.latitude]
                },
                "properties": {
                    "id": str(photo.id),
                    "image": request.build_absolute_uri(photo.image.url)
                }
            })

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        return JsonResponse(geojson)


@login_required
def profile_view(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            profile.save()
            return redirect('profile')
        else:
            form = ProfileForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'user': user,
        'profile': profile,
        'form': form
    })


def public_profile_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(Profile, user=user)

    return render(request, 'accounts/public_profile.html', {
        'user_profile': user,
        'profile': profile,
    })


def gallery_view(request):
    images = Photo.objects.all().order_by('-id')
    return render(request, 'photos/gallery.html', {'images': images})

@login_required
def my_photos_view(request):
    photos = Photo.objects.filter(add_id=request.user).order_by('-date_taken')
    return render(request, 'accounts/my_photos.html', {'photos': photos})


@login_required
def edit_photo_view(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id, add_id=request.user)

    if request.method == 'POST':
        photo.name = request.POST.get('name')
        photo.description = request.POST.get('description')
        photo.date_taken = request.POST.get('date_taken')

        tag_names = request.POST.get('tags', '').split(',')
        tags = []
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if tag_name:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                tags.append(tag)

        photo.save()
        photo.tags.set(tags)
        return redirect('my_photos')

    return redirect('my_photos')


@login_required
def delete_photo_view(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id, add_id=request.user)
    if request.method == 'POST':
        photo.delete()
    return redirect('my_photos')
