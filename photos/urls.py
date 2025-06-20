from django.urls import path
from . import views
from .views import PhotoView, MapView, PhotoGeoJSONView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', MapView.as_view(), name='map'),
    path('api/photos/', PhotoView.as_view(), name='photo_api'), # получаем JSON
    path('upload/', views.upload_photo, name='upload_photo'),
    path('photo/<int:photo_id>', views.view_photo, name='view_photo'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/photos/geojson/', PhotoGeoJSONView.as_view(), name='photos-geojson'),
    path('api/photos/year-range/', views.photo_year_range, name='photo_year_range'),  # Новый путь для диапазона годов
    path('profile/', views.profile_view, name='profile'),
    path('users/<int:user_id>/', views.public_profile_view, name='public_profile'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('myphotos/', views.my_photos_view, name='my_photos'),
    path('myphotos/<int:photo_id>/edit/', views.edit_photo_view, name='edit_photo'),
    path('myphotos/<int:photo_id>/delete/', views.delete_photo_view, name='delete_photo'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate_account'),
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='accounts/registration/password_reset_form.html'),
         name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/registration/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='accounts/registration/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/registration/password_reset_complete.html'),
         name='password_reset_complete'),
    path('politics/', views.politics, name='politics'),
    path('terms/', views.terms, name='terms'),
    path('photo/<int:photo_id>/report/', views.report_photo, name='report_photo'),
    path('moderation/', views.moderation_panel, name='moderation_panel'),
    path('moderation/photo/<int:photo_id>/edit/', views.edit_photo_moderator, name='edit_photo_moderator'),
    path('moderation/photo/<int:photo_id>/delete/', views.delete_photo_moderator, name='delete_photo_moderator'),
    path('moderation/photo/<int:photo_id>/demote', views.demote_photo, name='demote_photo'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('tag/<str:tag_name>/', views.photos_by_tag, name='photos_by_tag'),
    path('my-tags/', views.user_tags, name='user_tags'),
    path('tag/<str:tag_name>/', views.photos_by_tag, name='photos_by_tag'),
    path('tag-group/<str:tag_name>/', views.tag_group_photos, name='tag_group_photos'),
    path('api/user-tags/', views.user_tags, name='user-tags'),
]