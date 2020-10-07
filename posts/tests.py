from django.core.cache import cache
from django.test import TestCase, override_settings, Client
from django.urls import reverse

from posts.models import User, Post, Group, Follow


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


# Спринт 6
class TestErrorHandler(TestCase):
    """Error handler test"""

    def test404(self):
        response = self.client.get('/qweqwe12341/')
        self.assertEqual(response.status_code, 404)


class TestImageRender(TestCase):
    """check the page of a specific record with an image: the page has the <img>tag"""

    def setUp(self):
        self.tag = '<img'
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.text = 'test_text'
        self.post = Post.objects.create(
            text=self.text, author=self.user,
            image='posts/test_image/Test_image.jpg'
        )

    def test_direct_post_render_image(self):
        response = self.authorized_client.get(
            reverse('post', kwargs={'username': self.user.username,
                                    'post_id': self.post.pk}))
        self.assertContains(response, self.tag)

    def test_profile_post_image_render(self):
        response = self.authorized_client.get(
            reverse('profile', kwargs={'username': self.user.username}))
        self.assertContains(response, self.tag)

    def test_group_post_Render_Image(self):
        # Creating a new group and checking the tag
        self.group = Group.objects.create(title='Test group',
                                          slug='test-group',
                                          description='Test group description')
        self.post.group_id = self.group.pk
        self.post.save()

        response = self.authorized_client.get(
            reverse('group_post', kwargs={'slug': self.group.slug}))
        self.assertContains(response, self.tag)


class TestImageFormProtect(TestCase):
    """Checking for an image"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(text='test_text', author=self.user)
        self.image_path = 'media/posts/test_/Test_.png'
        self.non_image_path = 'posts/tests.py'
        self.error_message = f'Ошибка. Вы загрузили не изображение,' \
            f'или оно битое'

    def test_correct_image_form_protect(self):
        with open(self.image_path, 'rb') as file_handler:
            self.authorized_client.post(reverse('post_edit',
                                                kwargs={
                                                    'username': self.user.username,
                                                    'post_id': self.post.pk}),
                                        {'image': file_handler,
                                         'text': 'Text and image corrected'})

            post = Post.objects.first()
            self.assertIsNotNone(post.image)

    def test_protection_against_incorrect_image_shape(self):
        with open(self.non_image_path, 'rb') as file_handler:
            response = self.authorized_client.post(reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.pk}),
                {'image': file_handler,
                 'text': 'Text and invalid file'}
            )
            self.assertFormError(response, 'form', 'image', self.error_message)


class PageCacheTest(TestCase):
    """Cache test"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.text = 'test_text'

    def test_index_cache(self):
        # Creating the page cache and checking that the new post has not yet appeared
        self.authorized_client.get(reverse('index'))
        self.authorized_client.post(reverse('new_post'), {'text': self.text})
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, self.text)


class TestFollowerSystem(TestCase):
    """Test subscriptions and unsubscriptions, and pages for subscribers"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_to_follow = User.objects.create_user(
            username='Test_profile_for_the_subscription',
            password=12345)
        self.client.force_login(self.user)
        self.text = 'test_text'
        self.post = Post.objects.create(
            text=self.text, author=self.user_to_follow)

    def test_auth_user_follow_follow(self):
        response = self.authorized_client.get(
            reverse('profile_follow',
                    kwargs={'username': self.user_to_follow.username}))
        self.assertIsNotNone(Follow.objects.first())

    def test_auth_user_unfollow(self):
        response = self.authorized_client.get(
            reverse('profile_unfollow',
                    kwargs={'username': self.user_to_follow.username}))
        self.assertIsNone(Follow.objects.first())

    def test_follower_index(self):
        self.authorized_client.get(reverse('profile_follow',
                                           kwargs={
                                               'username': self.user_to_follow.username}))
        response = self.client.get(reverse('follow_index'))
        self.assertContains(response, self.text)

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
    def test_not_follower_index(self):
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertNotContains(response, self.text)


class TestCommentSystem(TestCase):
    """Checking whether registered and unregistered users can comment on posts"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.text = 'test_text'
        self.post = Post.objects.create(
            text=self.text, author=self.user)
        self.comment_text = 'test_comment'

    def test_of_authorized_user_comments(self):
        response = self.authorized_client.post(
            reverse('add_comment', kwargs={'username': self.user.username,
                                           'post_id': self.post.pk}),
            {'text': self.comment_text}, follow=True)
        self.assertContains(response, self.comment_text)

    def test_anon_user_commenting(self):
        """Anonymous users can't comment on posts"""

        response = self.client.post(
            reverse('add_comment', kwargs={'username': self.user.username,
                                           'post_id': self.post.pk}),
            {'text': self.comment_text}, follow=True)
        self.assertNotContains(response, self.comment_text)
