def check_context(self, context_object):
    """Проверка, что пост создается с верными данными."""
    self.assertEqual(context_object.author.username, self.user.username)
    self.assertEqual(context_object.text, self.post.text)
    self.assertEqual(context_object.group.title, self.group.title)
    self.assertEqual(context_object.image, self.post.image)


def check_comment(self, comment_object, form_data):
    self.assertEqual(comment_object.text, form_data['text'])
    self.assertEqual(comment_object.author.username, self.user.username)
    self.assertEqual(comment_object.post.id, self.post.id)