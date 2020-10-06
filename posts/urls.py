from django.urls import path

from . import views

urlpatterns = [
    # Главная страница
    path("", views.index, name="index"),
    # Умная ссылка
    path("group/<slug>/", views.group_posts, name="group_post"),

    path("follow/", views.follow_index, name="follow_index"),

    # Новый пост
    path("new/", views.new_post, name="new_post"),
    # Профайл пользователя
    path('<str:username>/', views.profile, name='profile'),
    # Просмотр записи
    path('<str:username>/<int:post_id>/', views.post_view, name='post'),
    path(
        '<str:username>/<int:post_id>/edit/',
        views.post_edit,
        name='post_edit'
    ),

    path('404/', views.page_not_found, name='error404'),
    path('500/', views.server_error, name='error500'),
    path("<username>/<int:post_id>/comment", views.add_comment, name="add_comment"),

    # path("follow/", views.follow_index, name="follow_index"),
    path("<str:username>/follow/", views.profile_follow, name="profile_follow"),
    path("<str:username>/unfollow/", views.profile_unfollow, name="profile_unfollow"),

]
