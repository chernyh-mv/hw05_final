from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Comment, Group, Post

User = get_user_model()

POST_STR: int = 15


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        model_fields = {
            self.post: self.post.text[:POST_STR],
            self.group: self.group.title,
            self.comment: self.comment.text,
        }
        for model, expected_value in model_fields.items():
            with self.subTest(model=model):
                self.assertEqual(expected_value, str(model))

    def test_posts_verbose_name_help_text(self):
        """verbose_name и help_text в полях совпадает с ожидаемым."""
        post_meta = self.post._meta.get_field('text')
        field_post = {
            post_meta.verbose_name: 'Текст поста',
            post_meta.help_text: 'Введите текст поста',
        }

        for field, text in field_post.items():
            with self.subTest():
                self.assertEqual(
                    field, text, 'Вот тут ошибочка')
