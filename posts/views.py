from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from posts.forms import PostForm, CommentForm
from .models import Post, Group, User, Follow
# import datetime
from django.core.paginator import Paginator


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)

    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
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
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
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
    user = get_object_or_404(User, username=username)
    paginator = Paginator(user.posts.all(), 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    following = None
    if not request.user.is_anonymous:
        following = Follow.objects.filter(user=request.user, author=user).exists()
    return render(request, 'profile.html', {
        'profile': user,
        'page': page,
        'paginator': paginator,
        'post_list': user.posts.all(),
        'following': following,
    })


def post_view(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    count = post.author.posts.count()
    comments = post.comments.all()
    form = CommentForm()
    return render(request, 'post.html', {
        'post': post,
        "profile": post.author,
        'my_post': count,
        "comments": comments,
        'form': form,
    })


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    if request.user != post.author:
        return redirect('post', username=username, post_id=post_id)
    # добавим в form свойство files
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect("post", username=request.user.username, post_id=post_id)

    return render(
        request, 'new_post.html', {'form': form, 'post': post, 'is_edit': True},
    )


def page_not_found(request, exception):
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
    post = get_object_or_404(Post, id=post_id, author__username=username)
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    if form.is_valid():
        new_comment = form.save(commit=False)
        new_comment.author = request.user
        new_comment.post = post
        new_comment.save()
        return redirect('post', username=username,
                        post_id=post_id)

    return render(request, 'includes/comments.html',
                  {'post': post,
                   'author': post.author,
                   'form': form,
                   'comments': comments}, )


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user).all()  #
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'follow.html',
                  {'page': page, 'paginator': paginator})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow_to_delete = Follow.objects.filter(user=request.user,
                                             author=author)
    if follow_to_delete.exists():
        follow_to_delete.delete()
    return redirect('profile', username=username)
