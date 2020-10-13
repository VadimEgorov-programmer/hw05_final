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
        self.image = self._create_image()
        self.file = self._create_file()

    def tearDown(self):
        self.image.close()

    def test_profile(self):
        """ After registration, a user's personal page (profile) is created) """
        response = self.authorized_client.get(reverse('profile', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['profile'], User)
        self.assertEqual(response.context['profile'].username, self.user.username)

    def test_auth_user_post_creation(self):
        """ An authorized user can post a message (new) """
        text = 'test_text'
        group = Group.objects.create(
            title='test_title', slug='test_slug', description='test_description')
        post = Post.objects.create(text=text, author=self.user, group=group)
        response = self.authorized_client.post(reverse('new_post'), {'text': text, 'group': group})
        self.assertEqual(response.status_code, 200)

        # Additionally check the post in the database
        post = Post.objects.first()
        post_count = Post.objects.count()
        self.assertEqual(post.text, text)
        self.assertEqual(post.group, group)
        self.assertEqual(post.author.username, self.user.username)
        self.assertEqual(post_count, 1)

    def test_for_an_unauthorized_redirect(self):
        """ An unauthorized visitor will not be able to publish a post (it redirects to the login page) """
        response = self.unauthorized_client.get(reverse('new_post'))
        self.assertRedirects(response=response,
                             expected_url='/auth/login/?next=/new/',
                             target_status_code=200)

    def test_anon_post_creation_post_request(self):
        """ Attempt to create a post without registration """
        text = 'test_text'
        self.unauthorized_client.post(reverse('new_post'), {'text': text})
        post_count = Post.objects.count()
        self.assertEqual(post_count, 0)

    def test_image_upload(self):
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        # Adding an image to the test post
        response = self.authorized_client.post(f'/username/{post.id}/edit/',
                                               {'text': post.text, 'image': self.image})

        # The image loaded successfully.
        self.assertRedirects(response, f'/username/{post.id}/')

        # We check the pages where the image has changed. This is the home page, profile and post
        for url in ('/', '/username/', f'/username/{post.id}/'):
            response = self.client.get(url)
            self.assertContains(response,
                                "<img",
                                msg_prefix=f'Image display error in {url}')

    def test_protection_against_incorrect_image_shape(self):
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        non_image_path = self.image
        error_message = f'Ошибка. Вы загрузили не изображение,' \
            f'или оно битое'
        with open(non_image_path, 'rb') as file_handler:
            response = self.authorized_client.post(reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'post_id': post.pk}),
                {'image': file_handler,
                 'text': 'Text and invalid file'}
            )
            self.assertFormError(response, 'form', 'image', error_message)


class PostEditTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_new_post_pages(self):
        """ After the post is published, a new entry appears on the main page of
        the site (index), on the user's personal page (profile), and on
         a separate page of the post (post)
        """
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        response = self.client.get(reverse('index'))
        self.assertContains(response, text, status_code=200)

        response = self.client.get(reverse('profile', args=('testuser')))
        self.assertContains(response, text, status_code=200)

        response = self.client.get(reverse('post', args=('self.user.username', post.id)))
        self.assertContains(response, text, status_code=200)

    def test_post_edit(self):
        """An authorized user can edit their post, and then the content
        of the post will change on all related pages."""
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        edit_post = 'This is new post for tests'
        new_group_post = 'This is new group post'
        group_post = Post.objects.create(
            text='This is test post in group',
            author=self.user, group=self.group)
        self.authorized_client.post(reverse('post_edit', args=[self.user.username,
                                                               post.id]),
                                    {'text': edit_post})
        self.authorized_client.post(reverse('post_edit', args=[self.user.username,
                                                               group_post.id]),
                                    {'text': new_group_post, 'group': self.group.id})
        edited_post = Post.objects.get(id=post.id)
        edited_group_post = Post.objects.get(id=group_post.id)
        self.assertEqual(edit_post, edited_post.text, msg="Post hasn't changed")
        self.assertEqual(new_group_post, edited_group_post.text,
                         msg="Group post hasn't changed")
        response = self.authorized_client.get(reverse('index'))
        self.assertContains(response, edited_post)
        self.assertContains(response, edited_group_post)
        response = self.authorized_client.get(reverse('profile',
                                                      args=[self.user.username]))
        self.assertContains(response, edited_post)
        self.assertContains(response, edited_group_post)
        response = self.client.get(reverse('group_post',
                                           args=[self.group.slug]))
        self.assertContains(response, edited_group_post)
        response = self.client.get(reverse('post', args=[self.user.username,
                                                         self.post.id]))
        response_group = self.client.get(reverse('post',
                                                 args=[self.user.username,
                                                       self.group_post.id]))
        self.assertContains(response, edited_post)
        self.assertContains(response_group, edited_group_post)


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

    def test_following(self):
        response = self.authorized_client.get(reverse('profile_follow', kwargs={'username': self.user.username}))
        self.assertTrue(
            Follow.objects.filter(user=self.authorized_client, author=self.user).exists(),
            "Follow object was not created")

    def test_the_user_is_subscribed_to_the_post_is_displayed(self):
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user_to_follow)
        response = self.authorized_client.get(reverse('profile_follow'))
        self.assertIn(
            post, response.context['page'],
            "follower can not see their subscriptions on /follow/ page")

    def test_unfollowing(self):
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user_to_follow)
        self.authorized_client.get(reverse('profile_unfollow', kwargs={'username': self.user.username}))
        response = self.authorized_client.get(reverse('profile_unfollow', kwargs={'username': self.user.username}))
        self.assertFalse(Follow.objects.filter(user=self.authorized_client, author=self.user).exists(),
                         "Follow object was not deleted")

        # test that author's posts do not appear on /follow/ for non-followers
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertNotIn(
            post, response.context['page'],
            "author not followed, but their post appears on /follow/")


class TestCommentSystem(TestCase):
    """Checking whether registered and unregistered users can comment on posts"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.comment_text = 'test_comment'

    def test_comments_authenticated(self):
        """ test that authenticated user can add comments """
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user)
        response = self.authorized_client.post(f'/username/{post.id}/comment/',
                                               {'text': 'Test'})
        self.assertTrue(
            Comment.objects.filter(post=post, author=self.authorized_client,
                                   text='Test').exists(),
            'Comment object was not created')
        go_to_post = self.authorized_client.post(reverse('post', kwargs={'username': self.user.username,
                                                                         'post_id': post.id}))
        self.assertRedirects(response, go_to_post)
        response = self.authorized_client.get(f'/username/{post.id}/')
        self.assertEqual(response.context['comments'][0].text, 'Test')

    def test_anon_user_commenting(self):
        """test that anonymous user cannot add comments"""
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user)
        response = self.unauthorized_client.post(
            reverse('add_comment', kwargs={'username': self.user.username,
                                           'post_id': post.pk}),
            {'text': self.comment_text}, follow=True)
        self.assertNotContains(response, self.comment_text)
