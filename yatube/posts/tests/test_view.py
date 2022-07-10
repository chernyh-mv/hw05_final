import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post, User
from .utils import check_comment, check_context


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


PAGE_SELECTION: int = 10


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gif_post = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image_for_post = SimpleUploadedFile(
            name='small.gif',
            content=cls.gif_post,
            content_type='image/gif',
        )
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=cls.image_for_post,
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            author=cls.user,
            post=cls.post,
        )
        cls.new_group = Group.objects.create(
            title='Другая группа',
            slug='test-slug_new',
            description='Другое описание',
        )
        cls.index = (
            'posts:index', 'posts/index.html', None
        )
        cls.group_list = (
            'posts:group_list', 'posts/group_list.html', [cls.group.slug]
        )
        cls.profile = (
            'posts:profile', 'posts/profile.html', [cls.post.author]
        )
        cls.post_detail = (
            'posts:post_detail', 'posts/post_detail.html', [cls.post.id]
        )
        cls.post_edit = (
            'posts:post_edit', 'posts/create_post.html', [cls.post.id]
        )
        cls.post_create = (
            'posts:post_create', 'posts/create_post.html', None
        )
        cls.page_with_paginator = [
            cls.index,
            cls.group_list,
            cls.profile,
        ]
        cls.page_without_paginator = [
            cls.post_create,
            cls.post_detail,
            cls.post_edit
        ]
        cls.all_pages = [
            *cls.page_with_paginator,
            *cls.page_without_paginator
        ]

    @classmethod
    def tearDownClass(cls):
        """Удаление временной папки после тестов."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.post.author)

    def make_reverse(self, expected_page: tuple):
        """Функция для формирования reverse."""
        page = expected_page[0]
        test_args = expected_page[2]
        return reverse(page, args=test_args)

    def post_response_context(self, response):
        """Для проверки Context на страницах:
        post_detail, create_post."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for page in self.all_pages:
            response = self.authorized_client.get(self.make_reverse(page))
            self.assertTemplateUsed(response, page[1])

    def test_post_index_group_profile_page_show_correct_context(self):
        """Проверяем Context на страницах index, group_list, profile."""
        for page in self.page_with_paginator:
            first_obj = self.authorized_client.get(
                self.make_reverse(page)).context['page_obj'][0]
            check_context(self, first_obj)

    def test_post_detail_show_correct_context(self):
        """Проверяем Context на странице post_detail."""
        response = self.authorized_client.get(
            self.make_reverse(self.post_detail)
        )
        form_data = {
            'text': self.comment.text,
        }
        first_comment = self.post.comments.all()[0]
        self.assertEqual(response.context.get('post'), self.post)
        check_comment(self, first_comment, form_data)
        
    def test_create_post_show_correct_context(self):
        """Проверяем Context на странице create_post."""
        response = self.authorized_client.get(
            self.make_reverse(self.post_create)
        )
        self.post_response_context(response)

    def test_post_edit_page_show_correct_context(self):
        """Проверяем Context на странице post_edit."""
        response = self.authorized_client.get(
            self.make_reverse(self.post_edit)
        )
        is_edit = response.context['is_edit']
        self.post_response_context(response)
        self.assertTrue(is_edit)

    def test_check_post_on_create(self):
        """Проверяем, что при создании поста с указанием группы
        этот пост появится на главной странице,
        на страницах группы и профайла."""
        for page in self.page_with_paginator:
            response = self.authorized_client.get(self.make_reverse(page))
            self.assertEqual(response.context['page_obj'][0], self.post)

    def test_group_post(self):
        """Проверка на ошибочное попадание поста не в ту группу."""
        response = self.authorized_client.get(reverse(
            'posts:group_list', args=[self.new_group.slug])
        )
        self.assertNotIn(self.post, response.context['page_obj'].object_list)

    def test_cache(self):
        """Проверка работы кеша."""
        cache.clear()
        post = Post.objects.create(
            author=self.user,
            text='Пост для проверки работы кеша',
        )
        response = self.guest_client.get(reverse(self.index[0]))
        cache_with_post = response.content
        post.delete()
        response = self.guest_client.get(reverse(self.index[0]))
        self.assertEqual(response.content, cache_with_post)
        cache.clear()
        response = self.guest_client.get(reverse(self.index[0]))
        self.assertNotEqual(response.content, cache_with_post)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.index = ('posts:index', None)
        cls.group_list = ('posts:group_list', [cls.group.slug])
        cls.profile = ('posts:profile', [cls.user])
        cls.pages_with_pagination = [
            cls.index,
            cls.group_list,
            cls.profile
        ]

        for i in range(13):
            Post.objects.create(
                text=f'Тестовый текст {i+1}',
                author=cls.user,
                group=cls.group,
                id=i
            )

    def setUp(self):
        self.client = Client()

    def test_first_page_contains_ten_records(self):
        """Первая страница index содержит десять записей."""
        for page in self.pages_with_pagination:
            reverse_name = reverse(page[0], args=page[1])
            response = self.client.get(reverse_name)
            self.assertEqual(
                len(response.context['page_obj']), PAGE_SELECTION)

    def test_second_page_contains_three_records(self):
        """Вторая страница index содержит три записи."""
        for page in self.pages_with_pagination:
            reverse_name = reverse(page[0], args=page[1])
            response = self.client.get(f'{reverse_name}' + '?page=2')
            second_page = Post.objects.count() % PAGE_SELECTION
            self.assertEqual(len(response.context['page_obj']), second_page)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(username='follower')
        cls.user_2 = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.user_2,
            text='Тестовый текст'
        )
        cls.follow = Follow.objects.filter(
            user=cls.user_1,
            author=cls.user_2
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_1)

    def test_authorized_user_can_follow_other_users(self):
        """Авторизованный пользователь может подписаться на автора."""
        follow_count = Follow.objects.count()
        self.assertFalse(self.follow.exists())
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            args=[self.user_2.username])
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(self.follow.exists())

    def test_authorized_user_can_unfollow_other_users(self):
        """Авторизованный пользователь может отписаться от автора."""
        self.follow
        follow_count = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            args=[self.user_2.username])
        )
        self.assertEqual(Follow.objects.count(), follow_count)
        self.assertFalse(self.follow.exists())

    def test_new_post_for_followers(self):
        """Новая запись пользователя появляется в ленте подписчиков."""
        Follow.objects.create(
            user=self.user_1,
            author=self.user_2)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_context = response.context['page_obj']
        self.assertIn(self.post, follow_context)

    def test_new_post_for_not_followers(self):
        """Новая запись пользователя не появляется в ленте
        у тех, кто не подписан."""
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_context = response.context['page_obj']
        self.assertNotIn(self.post, follow_context)
