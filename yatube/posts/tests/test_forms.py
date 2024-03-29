import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from http import HTTPStatus

from ..forms import PostForm
from ..models import Comment, Group, Post, User
from .utils import check_comment, check_context


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.post_image = SimpleUploadedFile(
            name='small.gif',
            content=cls.gif,
            content_type='image/gif',
        )
        cls.image_edit = SimpleUploadedFile(
            name='edit.gif',
            content=cls.gif,
            content_type='image/gif',
        )
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )
        cls.form = PostForm()
        cls.create = ('posts:post_create', None)
        cls.post_edit = ('posts:post_edit', [cls.post.pk])
        cls.post_comment = ('posts:add_comment', [cls.post.pk])
        cls.post_detail = ('posts:post_detail', [cls.post.pk])
        cls.post_profile = ('posts:profile', [cls.user])

    @classmethod
    def tearDownClass(cls):
        """Удаление временной папки после тестов."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def make_reverse(self, expected_page: tuple):
        """Функция для формирования reverse."""
        page = expected_page[0]
        test_args = expected_page[1]
        return reverse(page, args=test_args)

    def test_create_post_valid(self):
        """Проверка, что валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'author': self.post.author,
            'image': self.post_image
        }
        response = self.authorized_client.post(
            self.make_reverse(self.create), data=form_data, follow=True)
        first_object = response.context['page_obj'].object_list[0]
        self.assertRedirects(response, self.make_reverse(self.post_profile))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        check_context(self, first_object)

    def test_edit_post_valid(self):
        """Проверка, что валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Другой тестовый текст'
        }
        response = self.authorized_client.post(
            self.make_reverse(self.post_edit), data=form_data, follow=True)
        expected_object = response.context['post']
        self.assertRedirects(response, self.make_reverse(self.post_detail))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(expected_object.text, form_data['text'])

    def test_not_valid(self):
        """Проверка, что невалидная форма при создании поста или
        его редактировании не создает запись в Post,
        и страница отдаёт код 200."""
        posts_count = Post.objects.count()
        form_data = {
            'text': ''
        }
        reverse_page = [
            self.post_edit,
            self.create,
        ]
        for page in reverse_page:
            with self.subTest(page=page):
                response = self.authorized_client.post(
                    self.make_reverse(page), data=form_data, follow=True)
                self.assertEqual(Post.objects.count(), posts_count)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_add_comment_form(self):
        """Проверка, что валидная форма добавляет комментарий к посту."""
        comments_count = self.post.comments.all().count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            self.make_reverse(self.post_comment), data=form_data, follow=True)
        first_comment = self.post.comments.all()[0]
        self.assertRedirects(response, self.make_reverse(self.post_detail))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        check_comment(self, first_comment, form_data)
