from django.core.cache import cache
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils.html import escape

from posts.models import User, Post, Group, Follow, Comment
from PIL import Image
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile


class TestPosts(TestCase):
    def _create_image(self):
        # create a test image to avoid accessing real files during testing
        # https://dirtycoder.net/2016/02/09/testing-a-model-that-have-an-imagefield/

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(f, 'PNG')

        return open(f.name, mode='rb')

    def _create_file(self):
        file = SimpleUploadedFile('filename.txt', b'hello world', 'text/plain')
        return file

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.text = 'test_text'
        self.image = self._create_image()
        self.file = self._create_file()

    def tearDown(self):
        self.image.close()

    def test_auth_user_post_creation(self):
        # Go to your profile and check the redirect + create a group and post
        text = 'test_text'
        group = Group.objects.create(
            title='test_title', slug='test_slug', description='test_description')
        response = self.authorized_client.post(reverse('new_post'), {'text': text, 'group': group})
        self.assertEqual(response.status_code, 302)

        # Checking the similarity of the text, author, and group
        post = Post.objects.first()
        self.assertEqual(post.text, text)
        self.assertEqual(post.group, group)
        self.assertEqual(post.author.username, self.user.username)

    def test_anon_post_creation_redirect(self):
        response = self.unauthorized_client.get(reverse('new_post'))
        self.assertRedirects(response=response,
                             expected_url='/auth/login/?next=/new/',
                             target_status_code=200)

    def test_anon_post_creation_post_request(self):
        text = 'test_text'
        self.unauthorized_client.post(reverse('new_post'), {'text': text})
        post_count = Post.objects.count()
        self.assertEqual(post_count, 0)

    def test_edit_post_authenticated(self):
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        first_text = post.text
        new_text = "Checking text in the database"
        self.authorized_client.post(f'/username/{post.id}/edit/', {'text': new_text})
        post = Post.objects.first()
        self.assertEqual(first_text, post.new_text)

    def urls_test_profile_index_direct_post_view(self):
        """
        RLs for testing pages,
        User profile test,
        Home page test ('index'),
        The direct test page with posts,
        """
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': 'username', 'post_id': post.pk})]
        for url in urls:
            response = self.authorized_client.get(url)
            self.assertContains(response, text)
            self.assertContains(response, self.user.username)
            with self.subTest('Post is not on "' + url + '"'):
                if 'paginator' in response.context:
                    self.assertIn(
                        post, response.context['paginator'].object_list)
                else:
                    self.assertEquals(post, response.context['post'])

    def test_one_post_edit(self):
        # Creating a post
        text = 'text_test'
        post = Post.objects.create(
            text=text,
            author=self.user)
        text_edited = 'test_text_edit'
        # Main post group
        leo = Group.objects.create(
            title='lev_title_text',
            slug='leo_slug_text',
            description='New text_text')
        # We give the first group
        data = {
            'text': text_edited,
            'group': leo.id,
        }
        self.authorized_client.post(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': post.pk}
            ), data)
        # Looking at group changes
        post_edited = Post.objects.last()
        post_count = Post.objects.all().count()
        self.assertEqual(post, post_edited)
        self.assertEqual(post_edited.text, text_edited)
        self.assertEqual(post_edited.group, leo)
        self.assertEqual(post_count, 1)

    def urls(self):
        """
        Collects url of pages for testing
        """
        urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post_view', kwargs={'username': self.user.username, 'post_id': 1})]
        return urls

    def check_post_content(self, url, user, group, text, new_text):
        """
        Content of the post is checked
        """
        text = 'test_text'
        text_edited = 'test_text_edit'
        group = Group.objects.create(
            title='test_group',
            slug='test_group',
            description='test_text')
        response = self.authorized_client.get(url)
        self.assertEqual(response.context[user], self.user)
        self.assertEqual(response.context[group], group)
        self.assertEqual(response.context[text], text)
        self.assertEqual(response.context[new_text], text_edited)

    def check_post_on_pages(self):
        """
        Test for changing a post on all pages.
            """
        group = Group.objects.create(
            title='test_group',
            slug='test_group',
            description='test_text')
        text_edited = 'test_text_edit'
        self.authorized_client.post(
            reverse('new_post'),
            data={'text': self.text, 'group': group.id},
            follow=True
        )
        for url in (self.urls()):
            with self.subTest(url=url):
                self.check_post_content(url, self.user, group, self.text, text_edited)

        # Проверки для работы заданий Спринта 6

    def test_image_upload(self):
        # Adding an image to the test post
        response = self.authorized_client.post(f'/username/{self.post.id}/edit/',
                                               {'text': self.post.text, 'image': self.image})

        # The image loaded successfully.
        self.assertRedirects(response, f'/username/{self.post.id}/')

        # We check the pages where the image has changed. This is the home page, profile and post
        for url in ('/', '/username/', f'/username/{self.post.id}/'):
            response = self.client.get(url)
            self.assertContains(response,
                                "<img",
                                msg_prefix=f'Image display error in {url}')

    def test_protection_against_incorrect_image_shape(self):
        non_image_path = self.image
        error_message = f'Ошибка. Вы загрузили не изображение,' \
            f'или оно битое'
        with open(non_image_path, 'rb') as file_handler:
            response = self.authorized_client.post(reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.pk}),
                {'image': file_handler,
                 'text': 'Text and invalid file'}
            )
            self.assertFormError(response, 'form', 'image', error_message)


class PageCacheTest(TestCase):
    """Cache test"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_cache(self):
        text = 'test_text'
        # Creating the page cache and checking that the new post has not yet appeared
        self.authorized_client.get(reverse('index'))
        self.authorized_client.post(reverse('new_post'), {'text': text})
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, text)
        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(
            response,
            'test_text',
            msg_prefix="The post didn't appear on the main page after clearing the cache")


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

    def test_following(self):
        response = self.authorized_client.get(reverse('/Test_profile_for_the_subscription/follow'))
        self.assertTrue(
            Follow.objects.filter(user=self.follower, author=self.user).exists(),
            "Follow object was not created")

    def test_the_user_is_subscribed_to_the_post_is_displayed(self):
        response = self.authorized_client.get('/follow/')
        self.assertIn(
            self.post, response.context['page'],
            "follower can not see their subscriptions on /follow/ page")

    def test_unfollowing(self):
        self.authorized_client.get(reverse('/Test_profile_for_the_subscription/follow'))
        response = self.authorized_client.get(reverse('/Test_profile_for_the_subscription/unfollow'))
        self.assertFalse(Follow.objects.filter(user=self.follower, author=self.user).exists(),
                         "Follow object was not deleted")

        # test that author's posts do not appear on /follow/ for non-followers
        response = self.authorized_client.get(reverse('/follow/'))
        self.assertNotIn(
            self.post, response.context['page'],
            "author not followed, but their post appears on /follow/")


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

    def test_comments_authenticated(self):
        """ test that authenticated user can add comments """
        response = self.authorized_client.post(f'/username/{self.post.id}/comment/',
                                               {'text': 'Test checking how the comment works'})
        self.assertTrue(
            Comment.objects.filter(post=self.post, author=self.follower,
                                   text='Test checking how the comment works').exists(),
            'Comment object was not created')
        self.assertRedirects(response, f'/username/{self.post.id}/',
                             msg_prefix='user is not redirected to post page after commenting')
        response = self.authorized_client.get(f'/username/{self.post.id}/')
        self.assertEqual(response.context['comments'][0].text, 'Test checking how the comment works',
                         'comment not displayed on post page')

    def test_comments_anonymous(self):
        """ test that anonymous user cannot add comments """
        response = self.unauthorized_client.post(f'/testuser/{self.post.id}/comment/',
                                                 {'text': 'Test checking how the comment works'})
        self.assertFalse(
            Comment.objects.filter(post=self.post, text='Test checking how the comment works').exists(),
            'Comment object was created')
        self.assertRedirects(response, f'/auth/login/?next=/testuser/{self.post.id}/comment/',
                             msg_prefix='anonymous user is not redirected to login page')
