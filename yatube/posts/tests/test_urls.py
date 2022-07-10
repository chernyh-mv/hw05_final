from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from http import HTTPStatus

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.index = (
            '/', 'posts/index.html', None
        )
        cls.group_list = (
            '/group/test-slug/', 'posts/group_list.html', [cls.group.slug]
        )
        cls.profile = (
            '/profile/auth/', 'posts/profile.html', [cls.post.author]
        )
        cls.post_detail = (
            f'/posts/{cls.post.id}/', 'posts/post_detail.html', [cls.post.id]
        )
        cls.post_edit = (
            f'/posts/{cls.post.id}/edit/', 'posts/create_post.html',
            [cls.post.id]
        )
        cls.post_create = (
            '/create/', 'posts/create_post.html', None)
        cls.guest_page = [
            cls.index,
            cls.group_list,
            cls.profile,
            cls.post_detail
        ]
        cls.auth_page = [
            cls.post_detail,
            cls.post_create
        ]
        cls.all_page = [
            *cls.guest_page,
            *cls.auth_page
        ]
        cls.reverse_create = reverse('posts:post_create')
        cls.reverse_edit = reverse('posts:post_edit', args=[cls.post.id])

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.get(username='auth')
        self.post_author = Client()
        self.post_author.force_login(self.user)
        self.user = User.objects.create_user(username='not_author')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_status_code_for_urls_guest(self):
        """Доступность страниц для неавторизованного пользователя."""
        for address, template, test_args in self.guest_page:
            for page in self.guest_page:
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_status_code_for_urls_authorized(self):
        """Доступность страниц для авторизованного пользователя."""
        for address, template, test_args in self.all_page:
            for page in self.all_page:
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template_guest(self):
        """URL-адрес использует соответствующий шаблон
        для неавторизованного пользователя."""
        for address, template, test_args in self.guest_page:
            for page in self.guest_page:
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_correct_template_authorized(self):
        """URL-адрес использует соответствующий шаблон
        для авторизованного пользователя."""
        for address, template, test_args in self.all_page:
            for page in self.all_page:
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_redirect_create_for_anonymous(self):
        """Страницы /create/ и /edit/ перенаправят
        неавторизованного пользователя на страницу авторизации."""
        reverse_name = [
            self.reverse_create,
            self.reverse_edit
        ]
        for address in reverse_name:
            response = self.guest_client.get(address, follow=True)
            self.assertRedirects(response, f'/auth/login/?next={address}')

    def test_post_edit_for_not_author(self):
        """Страница по адресу /posts/<int:post_id>/edit/ перенаправит
        авторизованного пользователя (не автора поста) на страницу поста."""
        response = self.authorized_client.get(self.reverse_edit)
        self.assertRedirects(response, self.post_detail[0])

    def test_unexisting_page_error_404(self):
        """Проверка, что сайт выдаст ошибку 404 при несуществующем адресе."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
