from django.db import models
from django.forms import ModelForm
from posts.models import Post, Group, Comment
from django import forms


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ("group", "text", "image")
        required = {
            "group": False,
            "text": True,
        }
        labels = {
            "text": "Текст поста",
            "group": "Выберите сообщество"
        }
        help_texts = {
            "text": "Введите текст вашего поста"
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ("text",)
        labels = {
            "text": "Текст комментария",
        }
        help_texts = {
            "text": "Введит текст вашего комментария"
        }
        widgets = {'text': forms.Textarea({'rows': 3})}
