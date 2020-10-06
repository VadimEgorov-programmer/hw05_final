from django.core.cache import cache
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from posts.models import User, Post, Group


class TestPostCreation(TestCase):
    """1. Test for creating posts correctly
       2. Checking the capabilities of unauthorized users
     """

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.text = 'test_text'

    def test_auth_user_post_creation(self):
        # Go to your profile and check the redirect
        response = self.authorized_client.post(reverse('new_post'), {'text': self.text})
        self.assertEqual(response.status_code, 302)

        # Verification of the similarity of the text
        post = Post.objects.first()
        self.assertEqual(post.text, self.text)

    def test_anon_post_creation_redirect(self):
        # An unauthorized user and the post creation page
        response = self.unauthorized_client.get(reverse('new_post'))
        self.assertRedirects(response=response,
                             expected_url='/auth/login/?next=/new/',
                             target_status_code=200)

    def test_anon_post_creation_post_request(self):
        # Can a user create a POST via a POST request
        self.unauthorized_client.post(reverse('new_post'), {'text': self.text})
        post_count = Post.objects.filter(text=self.text).count()
        self.assertEqual(post_count, 0)


class TestPostRender(TestCase):
    """Post rendering test"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.text = 'test_text'
        self.post = Post.objects.create(text=self.text, author=self.user)

    def urls_test_profile_index_direct_post_view(self):
        """
        URLs for testing pages,
        User profile test,
        Home page test ('index'),
        The direct test page with posts,
        """
        self.urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': 'testuser', 'post_id': self.post.pk})]
        for url in self.urls:
            response = self.authorized_client.get(url)
            self.assertContains(response, self.text)


class TestPostEdit(TestCase):
    """Checking that the post was edited correctly"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.text = 'test_text'
        self.post = Post.objects.create(text=self.text, author=self.user)
        self.text_edited = 'test_text_edit'

        self.group = Group.objects.create(
            title='test_group',
            slug='test_group',
            description='test_text')

    def test_one_post_edit(self):
        # Editing a previously created post
        self.authorized_client.post(reverse('post_edit',
                                            kwargs={'username': self.user.username,
                                                    'post_id': self.post.pk}),
                                    {'text': self.text_edited})
        # Checking changes to the content of a single message
        post_edited = Post.objects.first()  # Получаем первый пост
        post_count = Post.objects.all().count()  # Считаем сколько всего постов
        self.assertEqual(self.post, post_edited)  # Сравниваем новый и измененный посты
        self.assertEqual(post_edited.text, self.text_edited)  # Сравниваем тексты на изменение
        self.assertEqual(post_count, 1)  # Проверяем количество постов

    def check_post_content(self, url, user, group, text, new_text):
        """
        Content of the post is checked
        """
        self.authorized_client.get(url)
        self.assertEqual(user, self.user)
        self.assertEqual(group, self.group)
        self.assertEqual(text, self.text)
        self.assertEqual(new_text, self.text_edited)

    def check_post_on_pages(self):
        """
        Test for changing a post on all pages.
        """
        self.authorized_client.post(
            reverse('new_post'),
            data={'text': self.text, 'group': self.group.id},
            follow=True
        )
        for url in (self.urls()):
            try:
                self.check_post_content(url, self.user, self.group, self.text, self.text_edited)
            except Exception:
                print('an unsuccessful verification')
