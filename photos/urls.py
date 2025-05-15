from django.urls import path
from . import views
from .views import PhotoView, MapView, PhotoGeoJSONView

urlpatterns = [
    path('', MapView.as_view(), name='map'),
    path('api/photos/', PhotoView.as_view(), name='photo_api'), # получаем JSON
    path('upload/', views.upload_photo, name='upload_photo'),
    path('photo/<int:photo_id>', views.view_photo, name='upload_photo'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/photos/geojson/', PhotoGeoJSONView.as_view(), name='photos-geojson'),
    path('profile/', views.profile_view, name='profile'),
    path('users/<int:user_id>/', views.public_profile_view, name='public_profile'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('myphotos/', views.my_photos_view, name='my_photos'),
    path('myphotos/<int:photo_id>/edit/', views.edit_photo_view, name='edit_photo'),
    path('myphotos/<int:photo_id>/delete/', views.delete_photo_view, name='delete_photo'),
]
