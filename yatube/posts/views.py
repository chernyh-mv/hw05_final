from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from posts.forms import CommentForm, PostForm
from posts.models import Comment, Follow, Group, Post, User
from posts.paginator import get_page


PAGE_SELECTION: int = 10


def index(request):
    """Главная страница."""
    post_list = Post.objects.select_related('author', 'group')
    page_obj = get_page(post_list, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Страница с постами, выбранной группы."""
    group = get_object_or_404(Group, slug=slug)
    post_list = group.group.all()
    page_obj = get_page(post_list, request)
    context = {
        'page_obj': page_obj,
        'group': group,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Страница профайла пользователя."""
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    posts_count = post_list.count()
    page_obj = get_page(post_list, request)
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(
            user=request.user,
            author=author
        ).exists()
    )
    context = {
        'author': author,
        'posts_count': posts_count,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Страница для просмотра отдельного поста."""
    post = get_object_or_404(Post.objects.select_related('author'), pk=post_id)
    comments = Comment.objects.filter(post=post)
    posts_count = post.author.posts.count()
    comment_count = comments.count()
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'posts_count': posts_count,
        'form': form,
        'comments': comments,
        'comment_count': comment_count,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Страница для создания поста."""
    form = PostForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        form.save()
        return redirect('posts:profile', username=post.author)
    form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    """Страница для редактирования поста."""
    post = get_object_or_404(Post, id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    else:
        if request.method == "POST" and form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            form.save()
            return redirect('posts:post_detail', post_id)
    return render(
        request,
        'posts/create_post.html',
        {'form': form, 'post': post, 'is_edit': True}
    )


@login_required
def add_comment(request, post_id):
    """Функция комментирования поста авторизованным пользователем."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Старница с постами авторов, на которых подписан текущий пользователь."""
    template_name = 'posts/follow.html'
    post_list = Post.objects.filter(author__following__user=request.user).all()
    page_obj = get_page(post_list, request)
    context = {
        'following': True,
        'page_obj': page_obj,
    }
    return render(request, template_name, context)


@login_required
def profile_follow(request, username):
    """Подписаться на автора."""
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Отписаться от автора."""
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
