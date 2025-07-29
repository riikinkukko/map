from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import status
from django.views.generic import TemplateView
from rest_framework.views import APIView
from pastvu.settings import MODERATOR_IDS
from .decorators import moderator_required
from .serializers import PhotoSerializer
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from .forms import ProfileForm, PhotoReportForm
from .models import Photo, Tag, Comment, Profile, TagMergeRequest, TagGroup
from .forms import PhotoForm, RegisterForm, PhotoEditForm
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from .forms import CommentForm
from django.core.mail import EmailMessage
from django.db.models import Min, Max
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import LoginAttempt
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from threading import Thread
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Count, Avg, F, IntegerField
from django.db.models.functions import Cast
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

MODERATOR_IDS = settings.MODERATOR_IDS

@login_required
def upload_photo(request):
    is_superuser = request.user.is_superuser or request.user.id in getattr(settings, "MODERATOR_IDS", [])

    if request.method == 'POST':
        post_data = request.POST.copy()

        tag_name = post_data.get('tag')
        if tag_name:
            tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
            post_data['tag'] = tag_obj.id

        form = PhotoForm(post_data, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.add_id = request.user
            photo.save()
            form.save_m2m()
            return HttpResponseRedirect(f"{reverse('map')}?lat={photo.latitude}&lng={photo.longitude}")
    else:
        form = PhotoForm()

    return render(request, 'photos/upload.html', {
        'form': form,
        'is_superuser': is_superuser,
    })

@method_decorator(ratelimit(key='ip', rate='1000/d', block=True), name='dispatch')
class MapView(TemplateView):
    template_name = 'photos/map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_superuser'] = True if self.request.user.is_authenticated and (self.request.user.is_superuser or self.request.user.id in getattr(settings, "MODERATOR_IDS", [])) else False
        return context


@method_decorator(cache_page(60*5), name='dispatch')
class ClusteredPhotoView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            xmin = float(request.GET.get('xmin'))
            xmax = float(request.GET.get('xmax'))
            ymin = float(request.GET.get('ymin'))
            ymax = float(request.GET.get('ymax'))
            zoom = int(request.GET.get('zoom'))
        except (TypeError, ValueError):
            return Response({"error": "Invalid or missing coordinates/zoom"}, status=400)

        year = request.GET.get('year')
        tag = request.GET.get('tag')

        photos = Photo.objects.filter(
            latitude__gte=ymin, latitude__lte=ymax,
            longitude__gte=xmin, longitude__lte=xmax
        )

        if year:
            photos = photos.filter(date_taken__year=year)

        if tag:
            photos = photos.filter(tag__name=tag)

        grid_size = self._get_grid_size(zoom)

        clusters = photos.annotate(
            lat_bin=Cast(F('latitude') / grid_size, IntegerField()),
            lon_bin=Cast(F('longitude') / grid_size, IntegerField())
        ).values('lat_bin', 'lon_bin').annotate(
            count=Count('id'),
            avg_lat=Avg('latitude'),
            avg_lon=Avg('longitude')
        )

        result = []
        for c in clusters:
            result.append({
                "type": "cluster" if c['count'] > 1 else "point",
                "coordinates": [c['avg_lon'], c['avg_lat']],
                "count": c['count']
            })

        return JsonResponse({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": cluster["coordinates"]
                    },
                    "properties": {
                        "count": cluster["count"],
                        "type": cluster["type"]
                    }
                }
                for cluster in result
            ]
        })

    def _get_grid_size(self, zoom):
        if zoom <= 5:
            return 1.0
        elif zoom <= 8:
            return 0.5
        elif zoom <= 10:
            return 0.2
        elif zoom <= 12:
            return 0.1
        elif zoom <= 14:
            return 0.05
        else:
            return 0.01

class PhotoView(APIView):
    def get(self, request, *args, **kwargs):
        xmin = request.GET.get('xmin')
        ymin = request.GET.get('ymin')
        xmax = request.GET.get('xmax')
        ymax = request.GET.get('ymax')
        year = request.GET.get('year')
        tag = request.GET.get('tag')

        if not (xmin and ymin and xmax and ymax):
            return Response({"error": "Missing required parameters."}, status=400)

        try:
            xmin = float(xmin)
            ymin = float(ymin)
            xmax = float(xmax)
            ymax = float(ymax)
        except ValueError:
            return Response({"error": "Invalid coordinate values."}, status=400)

        photos = Photo.objects.filter(
            latitude__gte=ymin, latitude__lte=ymax,
            longitude__gte=xmin, longitude__lte=xmax
        )

        if year:
            photos = photos.filter(date_taken__year=year)

        if tag:
            photos = photos.filter(tag__name=tag)

        serializer = PhotoSerializer(photos, many=True)
        return Response(serializer.data)


def view_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    comments = photo.comments.select_related('user').order_by('created_at')
    form = CommentForm()
    report_form = PhotoReportForm()

    is_superuser = request.user.is_authenticated and (
            request.user.is_superuser or request.user.id in getattr(settings, "MODERATOR_IDS", [])
    )

    if request.user.is_authenticated:
        if request.method == 'POST' and 'tag_name' in request.POST:
            if request.user == photo.add_id:
                tag_name = request.POST.get('tag_name', '').strip()
                if tag_name:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    photo.tag = tag
                    photo.save()

                    group, created = TagGroup.objects.get_or_create(tag=tag)
                    group.members.add(request.user)

                    return redirect('view_photo', photo_id=photo.id)

        if request.method == 'POST' and 'comment_id' in request.POST:
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(Comment, id=comment_id)
            if request.user == comment.user or is_superuser:
                new_text = request.POST.get('text', '').strip()
                if new_text:
                    comment.text = new_text
                    comment.save()
                    return redirect('view_photo', photo_id=photo.id)

        elif request.method == 'POST':
            if request.user.is_authenticated:
                form = CommentForm(request.POST)
                if form.is_valid():
                    comment = form.save(commit=False)
                    comment.photo = photo
                    comment.user = request.user
                    comment.save()
                    return redirect('view_photo', photo_id=photo.id)
            else:
                return redirect('login')

    return render(request, 'photos/photo.html', {
        'photo': photo,
        'form': form,
        'comments': comments,
        'is_superuser': is_superuser,
        'report_form': report_form,
    })


def photos_by_tag(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    photos = Photo.objects.filter(tag=tag).select_related('add_id')
    users_with_tag = User.objects.filter(photos_added__tag=tag).distinct().exclude(id=request.user.id)

    sent_requests = TagMergeRequest.objects.filter(from_user=request.user, tag=tag)
    received_requests = TagMergeRequest.objects.filter(to_user=request.user, tag=tag)

    tag_group = TagGroup.objects.filter(tag=tag).first()
    tag_group_members = tag_group.members.all() if tag_group else []

    if request.method == 'POST' and request.user.is_authenticated:
        action = request.POST.get('action')

        if action == 'send':
            to_user_id = request.POST.get('to_user_id')
            to_user = get_object_or_404(User, id=to_user_id)
            TagMergeRequest.objects.get_or_create(
                from_user=request.user,
                to_user=to_user,
                tag=tag
            )
        elif action in ['accept', 'decline']:
            request_id = request.POST.get('request_id')
            merge_request = get_object_or_404(TagMergeRequest, id=request_id, to_user=request.user)
            merge_request.status = 'accepted' if action == 'accept' else 'declined'
            merge_request.save()

            if action == 'accept':
                merge_request = get_object_or_404(TagMergeRequest, id=request_id, to_user=request.user)
                merge_request.status = 'accepted'
                merge_request.save()

                target_group, created = TagGroup.objects.get_or_create(tag=merge_request.tag,
                                                                       members=merge_request.to_user)

                join_tag_group(merge_request.from_user, merge_request.tag, target_group)

        return redirect('photos_by_tag', tag_name=tag.name)

    return render(request, 'photos/photos_by_tag.html', {
        'tag': tag,
        'photos': photos,
        'users_with_tag': users_with_tag,
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'tag_group_members': tag_group_members,
    })


@login_required
def tag_group_photos(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    try:
        group = TagGroup.objects.get(tag=tag)
    except TagGroup.DoesNotExist:
        return render(request, 'photos/not_in_group.html', {'tag': tag})

    if request.user not in group.members.all():
        return render(request, 'photos/not_in_group.html', {'tag': tag})

    photos = Photo.objects.filter(tag=tag, add_id__in=group.members.all())

    return render(request, 'photos/tag_group_photos.html', {
        'tag': tag,
        'group': group,
        'photos': photos,
    })


def join_tag_group(user, tag, target_group):
    user_group = TagGroup.objects.filter(tag=tag, members=user).first()

    if user_group:
        if user_group == target_group:
            return target_group
        else:
            target_group.members.add(*user_group.members.all())
            user_group.delete()
    else:
        target_group.members.add(user)

    return target_group


@require_POST
@login_required
def report_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    report_form = PhotoReportForm(request.POST)
    if report_form.is_valid() and not photo.reported:
        photo.reported = True
        photo.reported_at = report_form.cleaned_data['reason']
        photo.save()
    return redirect('view_photo', photo_id=photo.id)

def send_activation_email(user, request):
    current_site = get_current_site(request)
    mail_subject = 'Активация аккаунта'
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_link = f"http://{current_site.domain}/activate/{uid}/{token}/"

    message = render_to_string('emails/activation_email.html', {
        'user': user,
        'activation_link': activation_link,
    })

    email = EmailMessage(mail_subject, message, to=[user.email])
    email.content_subtype = 'html'
    email.send()


def register(request):
    expiration_time = timezone.now() - timedelta(minutes=10)
    User.objects.filter(is_active=False, date_joined__lt=expiration_time).delete()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()

            Thread(target=send_activation_email, args=(user, request)).start()

            return render(request, 'accounts/registration/confirmation_sent.html')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'accounts/registration/activation_success.html')
    else:
        return render(request, 'accounts/registration/activation_failed.html')


def login_view(request):
    LoginAttempt.objects.filter(last_attempt__lt=timezone.now() - timedelta(hours=24)).delete()
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        print(username, password)
        attempt, _ = LoginAttempt.objects.get_or_create(username=username)

        if attempt.is_blocked():
            messages.error(request, 'Слишком много попыток входа. Попробуйте снова через час.')
            return redirect('login')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            attempt.reset_attempts()
            return redirect('/')
        else:
            attempt.attempts += 1
            if attempt.attempts >= 10:
                attempt.blocked_until = timezone.now() + timedelta(hours=1)
            attempt.save()
            messages.error(request, 'Неверный логин или пароль')
            return redirect('login')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('/')


class PhotoGeoJSONView(APIView):
    def get(self, request, *args, **kwargs):
        year = request.GET.get('year')
        tag = request.GET.get('tag')
        if not tag or tag.lower() == 'null':
            tag = None

        photos = Photo.objects.all()

        if year:
            try:
                year = int(year)
                photos = photos.filter(date_taken__year=year)
            except ValueError:
                return JsonResponse({"error": "Invalid year"}, status=400)

        if tag:
            photos = photos.filter(tag__name=tag)
            print(tag)

        bbox = request.GET.get('bbox')
        if bbox:
            try:
                lat1, lon1, lat2, lon2 = map(float, bbox.split(','))
                photos = photos.filter(latitude__gte=min(lat1, lat2), latitude__lte=max(lat1, lat2),
                                       longitude__gte=min(lon1, lon2), longitude__lte=max(lon1, lon2))
            except ValueError:
                return JsonResponse({"error": "Invalid bbox"}, status=400)

        features = []
        for photo in photos:
            if photo.latitude is None or photo.longitude is None:
                continue

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [photo.longitude, photo.latitude]
                },
                "properties": {
                    "id": str(photo.id),
                    "image": request.build_absolute_uri(photo.image.url),
                    "date_taken": photo.date_taken.strftime("%Y-%m-%d"),
                    "tag": photo.tag.name if photo.tag else None,
                }
            })

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        return JsonResponse(geojson)


@api_view(['GET'])
def user_tags(request):
    if not request.user.is_authenticated:
        return Response([], status=401)

    try:
        tags = Photo.objects.filter(add_id=request.user.id).values_list('tag__name', flat=True).distinct()
        return Response(list(set(tags)))

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def photo_year_range(request):
    """Возвращает минимальный и максимальный год из базы данных"""
    year_range = Photo.objects.aggregate(
        min_year=Min('date_taken__year'),
        max_year=Max('date_taken__year')
    )
    return JsonResponse({
        'min_year': year_range['min_year'],
        'max_year': year_range['max_year']
    })


@login_required
def profile_view(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.user.is_authenticated and (request.user.is_superuser or request.user.id in getattr(settings, "MODERATOR_IDS", [])):
        is_superuser = True
    else:
        is_superuser = False

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
        'form': form,
        'is_superuser': is_superuser,
    })


def public_profile_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(Profile, user=user)
    if request.user.is_authenticated and (request.user.is_superuser or request.user.id in getattr(settings, "MODERATOR_IDS", [])):
        is_superuser = True
    else:
        is_superuser = False
    return render(request, 'accounts/public_profile.html', {
        'user_profile': user,
        'profile': profile,
        'is_superuser': is_superuser,
})


def gallery_api(request):
    page_number = int(request.GET.get('page', 1))
    images = Photo.objects.all().order_by('-id')
    paginator = Paginator(images, 16)
    page_obj = paginator.get_page(page_number)

    html = render_to_string('partials/gallery_items.html', {'images': page_obj})

    return JsonResponse({
        'html': html,
        'has_next': page_obj.has_next()
    })


def gallery_view(request):
    is_superuser = request.user.is_authenticated and (
        request.user.is_superuser or request.user.id in getattr(settings, "MODERATOR_IDS", [])
    )

    return render(request, 'photos/gallery.html', {
        'is_superuser': is_superuser,
    })


@login_required
def my_photos_view(request):
    year = request.GET.get('year')
    photos = Photo.objects.filter(add_id=request.user).order_by('-date_taken')
    if request.user.is_authenticated and (request.user.is_superuser or request.user.id in getattr(settings, "MODERATOR_IDS", [])):
        is_superuser = True
    else:
        is_superuser = False
    if year:
        photos = photos.filter(date_taken__year=year)

    return render(request, 'accounts/my_photos.html', {
        'photos': photos,
        'selected_year': year,
        'is_superuser': is_superuser,
    })


@login_required
def edit_photo_view(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id, add_id=request.user)

    if request.method == 'POST':
        photo.name = request.POST.get('name')
        photo.description = request.POST.get('description')
        photo.date_taken = request.POST.get('date_taken')

        tag_name = request.POST.get('tag')

        if tag_name:
            photo.tag = photo.name = request.POST.get('tag')

        photo.save()

        return redirect('my_photos')

    return redirect('my_photos')


@login_required
def delete_photo_view(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id, add_id=request.user)
    if request.method == 'POST':
        photo.delete()
    return redirect('my_photos')


def politics(request):
    return render(request, 'accounts/registration/politics.html')

def terms(request):
    return render(request, 'accounts/registration/terms.html')


@moderator_required
def moderation_panel(request):
    reported_photos = Photo.objects.filter(reported=True)

    return render(request, 'moderation/panel.html', {
        'photos': reported_photos,
    })

@moderator_required
def edit_photo_moderator(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)

    if request.method == 'POST':
        form = PhotoEditForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            form.save()
            return redirect('moderation_panel')
    else:
        form = PhotoEditForm(instance=photo)

    return render(request, 'moderation/edit_photo.html', {
        'form': form,
        'photo': photo
    })

@moderator_required
def delete_photo_moderator(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    photo.delete()
    return redirect('moderation_panel')

@moderator_required
def demote_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    photo.reported = False
    photo.save()
    return redirect('moderation_panel')

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user == comment.user or request.user.is_superuser or request.user.id in getattr(settings, "MODERATOR_IDS", []):
        photo_id = comment.photo.id
        comment.delete()
        return redirect('view_photo', photo_id=photo_id)
    return redirect('map')
