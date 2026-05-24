from django.shortcuts import render, get_object_or_404, redirect
from .models import Category, Post, Comment
from .forms import UserForm, PostForm, CommentForm
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.views.generic import DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404


User = get_user_model()

def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=profile_user).annotate(comment_count=Count('comments')).order_by('-pub_date')
    if request.user != profile_user:
        posts = posts.filter(is_published=True, pub_date__lte=timezone.now(), category__is_published=True)
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'profile': profile_user,
        'page_obj': page_obj,
    }
    return render(request, 'blog/profile.html', context)

@login_required
def edit_profile(request):
    # Форма будет работать с текущим пользователем (request.user)
    form = UserForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        # После успеха возвращаемся в свой профиль
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/user.html', {'form': form})

@login_required
def post_create(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    context = {'form': form}
    return render(request, 'blog/create.html', context)

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=post_id)
    context = {'form': form, 'is_edit': True}
    return render(request, 'blog/create.html', context)

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', id=post_id)

@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=post_id)
    context = {'form': form,
               'comment': comment}
    return render(request, 'blog/comment.html', context)


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        instance = get_object_or_404(Post, pk=kwargs['post_id'])
        if instance.author != request.user:
            return redirect('blog:post_detail', id=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)
    def get_success_url(self):
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})

class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        instance = get_object_or_404(Comment, pk=kwargs['comment_id'])
        if instance.author != request.user:
            return redirect('blog:post_detail', id=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'id': self.kwargs['post_id']})

def index(request):
    post_list = (
        Post.objects.select_related('category', 'author', 'location')
        .filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    )
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    context = {
        'page_obj': page_obj,
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, id):
    # post = get_object_or_404(
    #     Post.objects.select_related('category', 'author', 'location'),
    #     id=id,
    #     is_published=True,
    #     pub_date__lte=timezone.now(),
    #     category__is_published=True
    # )
    # context = {
    #     'post': post,
    # }
    # return render(request, 'blog/detail.html', context)

    post = get_object_or_404(Post, id=id)

    if post.author != request.user:
        if not (
                post.is_published and
                post.pub_date <= timezone.now() and
                post.category.is_published
        ):
            raise Http404("Пост не найден или еще не опубликован")
    form = CommentForm()
    comments = post.comments.all()

    context = {'post': post,
               'form': form,
               'comments': comments}
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = Post.objects.select_related('author', 'location').filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)
