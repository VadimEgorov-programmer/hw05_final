from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from posts.forms import PostForm, CommentForm
from .models import Post, Group, User
# import datetime
from django.core.paginator import Paginator


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)  # показывать по 10 записей на странице.

    page_number = request.GET.get('page')  # переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # получить записи с нужным смещением
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator}
    )


def group_posts(request, slug):
    '''
    Функция get_object_or_404 получает по заданным критериям объект
    из базы данных или возвращает сообщение об ошибке, если объект не найден.
    '''
    group = get_object_or_404(Group, slug=slug)
    post_list = Post.objects.filter(group=group).all()
    paginator = Paginator(post_list, 10)  # показывать по 10 записей на странице.
    page_number = request.GET.get('page')  # переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # получить записи с нужным смещением
    return render(
        request,
        'group.html',
        {'page': page, 'paginator': paginator,
         'group': group, 'posts': post_list, }
    )


@login_required
def new_post(request):
    user = request.user
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('index')
    return render(request, 'new_post.html', {'form': form})


def profile(request, username):
    user = get_object_or_404(User, username=username)  # Если отсуствует имя пользователя, то выдаем ошибку 404
    post_list = Post.objects.filter(author=user).all()  # Получаем все посты профиля определённого пользователя
    my_post = Post.objects.filter(author=user).count()  # Считаем количество постов определённого пользователя
    paginator = Paginator(post_list, 10)  # Показываем 10 записей на странице
    page_number = request.GET.get('page')  # Переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # Получаем записи с нужным смещением страниц
    return render(request, 'profile.html', {
        'profile': user,
        'my_post': my_post,
        'page': page,
        'paginator': paginator,
        'post_list': post_list,
    })


def post_view(request, username, post_id):
    user = get_object_or_404(User, username=username)  # Если отстутсвует такое имя пользователя, то выдаем ошибку 404
    post = get_object_or_404(Post, id=post_id, author=user)
    # Если отсутствует определённый пост
    # и определённый автор, то выдаём ошибку 404"""
    my_post = Post.objects.filter(author=user).count()  # Считаем количество постов определённого пользователя
    comments = post.comment_post.all()
    return render(request, 'post.html', {
        'post': post,
        "profile": user,
        'my_post': my_post,
        "comments": comments,
    })


# @login_required
# def post_edit(request, username, post_id):
#     author = get_object_or_404(User, username=username)
#     if request.user != author:
#         return redirect("post", username=request.user.username, post_id=post_id)
#     post = get_object_or_404(Post, id=post_id, author=author)
#     form = PostForm(request.POST or None, instance=post)
#     if form.is_valid():
#         form.save()
#         return redirect("post", username=request.user.username, post_id=post_id)
#
#     return render(
#         request, "", {"form": form, "post": post}, )


@login_required
def post_edit(request, username, post_id):
    profile = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id, author=profile)
    if request.user != profile:
        return redirect('post', username=username, post_id=post_id)
    # добавим в form свойство files
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect("post", username=request.user.username, post_id=post_id)

    return render(
        request, 'new_post.html', {'form': form, 'post': post},
    )


def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author = get_object_or_404(User, username=username)
    comments = post.comment_post.all()

    form = CommentForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.author = request.user
            new_comment.post = post
            new_comment.save()
            return redirect('post', username=username,
                            post_id=post_id)

    return render(request, 'comments.html',
                  {'post': post,
                   'author': author,
                   'form': form,
                   'comments': comments},)
