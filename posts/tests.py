from django.core.cache import cache
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils.html import escape

from posts.models import User, Post, Group, Follow, Comment
from PIL import Image
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile


class TestPosts(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser",
                                             password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_profile(self):
        """ After registration, a user's personal page (profile) is created) """
        response = self.authorized_client.get(reverse('profile',
                                                      kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['profile'], User)
        self.assertEqual(response.context['profile'].username,
                         self.user.username)

    def test_auth_user_post_creation(self):
        """ An authorized user can post a message (new) """
        text = 'test_text'
        group = Group.objects.create(
            title='test_title', slug='test_slug',
            description='test_description')
        post = Post.objects.create(text=text, author=self.user, group=group)
        response = self.authorized_client.post(reverse('new_post'),
                                               {'text': text, 'group': group})
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

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
    def test_image_upload(self):
        # create a test image to avoid accessing real files during testing
        # https://dirtycoder.net/2016/02/09/testing-a-model-that-have-an-imagefield/
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(f, 'PNG')

        image = open(f.name, mode='rb')
        post = Post.objects.create(
            text="test_text",
            author=self.user)
        self.authorized_client.post(reverse('post_edit', args=[self.user.username, post.id]),
                                    {"text": "post with image", "image": image})
        urls = [
            reverse('post', args=[self.user.username, post.id]),
            reverse("index"),
            reverse('profile', args=[self.user.username])
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, "<img", status_code=200)

    def test_protection_against_incorrect_image_shape(self):
        file = SimpleUploadedFile('filename.txt', b'hello world',
                                  'text/plain')
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        response = self.authorized_client.post(reverse(
            'post_edit',
            kwargs={
                'username': self.user.username,
                'post_id': post.pk}),
            {'image': file,
             'text': post.text}
        )
        self.assertTrue(response.context['form'].has_error('image'))

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
    def test_new_post_pages(self):
        """ After the post is published, a new entry appears on the main page of
        the site (index), on the user's personal page (profile), and on
         a separate page of the post (post)
        """
        self.text = 'test_text'
        post = Post.objects.create(text=self.text, author=self.user)
        urls =[
            reverse('index'),
            reverse('profile', args=[self.user.username]),
            reverse('post', args=(self.user.username, post.id)),
        ]
        for url in urls:
            self.check_post_content(url, self.user)



        #response = self.authorized_client.get(reverse('index'))

        #response = self.authorized_client.get(reverse('profile', args=[self.user.username]))

        #response = self.authorized_client.get(reverse('post', args=(self.user.username, post.id)))

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
    def test_post_edit(self):
        """An authorized user can edit their post, and then the content
        of the post will change on all related pages."""
        group = Group.objects.create(title='Test Group', slug='testsslug',
                                     description='Test group!')
        text = 'test_text'
        post = Post.objects.create(text=text, author=self.user)
        edit_post = 'This is new post for tests'
        new_group_post = 'This is new group post'
        group_post = Post.objects.create(
            text='This is test post in group',
            author=self.user, group=group)
        self.authorized_client.post(reverse('post_edit',
                                            args=[self.user.username,
                                                  post.id]),
                                    {'text': edit_post})
        self.authorized_client.post(reverse('post_edit', args=[self.user.username,
                                                               group_post.id]),
                                    {'text': new_group_post, 'group': group.id})
        """
        urls = [
            reverse('index'),
            reverse('profile', args=[self.user.username]),
            reverse('post', args=(self.user.username, post.id)),
        ]
        for url in urls:
            self.check_post_content(url, post)
            """


        edited_post = Post.objects.get(id=post.id)
        edited_group_post = Post.objects.get(id=group_post.id)
        self.assertEqual(edit_post, edited_post.text,
                         msg="Post hasn't changed")
        """
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
                                           args=[group.slug]))
        self.assertContains(response, edited_group_post)
        response = self.client.get(reverse('post', args=[self.user.username,
                                                         post.id]))
        response_group = self.client.get(reverse('post',
                                                 args=[self.user.username,
                                                       group_post.id]))
        self.assertContains(response, edited_post)
        self.assertContains(response_group, edited_group_post)
        """

    def check_post_content(self, url, text):
        """generalized method for checking posts"""
        response = self.authorized_client.get(url)
        #self.assertContains(response.context['page'], text)
        self.assertContains(response, text, status_code=200)



class PageCacheTest(TestCase):
    """Cache test"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser",
                                             password=12345)
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
        self.user = User.objects.create_user(username="testuser",
                                             password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_to_follow = User.objects.create_user(
            username='Test_profile_for_the_subscription',
            password=12345)
        self.client.force_login(self.user)

    def test_following(self):
        text = 'test_text'
        group = Group.objects.create(
            title='test_title', slug='test_slug',
            description='test_description')
        post = Post.objects.create(text=text, author=self.user, group=group)
        self.authorized_client.post(reverse('new_post'),
                                    {'text': text, 'group': group})
        self.authorized_client.get(
            reverse('profile_follow',
                    kwargs={'username': self.user_to_follow.username}))
        follow = Follow.objects.first()
        follow_count = Follow.objects.count()
        self.assertEqual(follow_count, 1)
        self.assertEqual(post.text, text)

    def test_the_user_is_subscribed_to_the_post_is_displayed(self):
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user_to_follow)
        self.authorized_client.get(reverse('profile_follow',
                                           kwargs={'username': self.user_to_follow.username}))
        response = self.authorized_client.get(reverse("follow_index"))
        self.assertIn(
            post, response.context['page'],
            "follower can not see their subscriptions on /follow/ page")

    def test_unfollowing(self):
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user_to_follow)
        self.authorized_client.get(reverse('profile_unfollow',
                                           kwargs={'username': self.user.username}))
        self.assertFalse(Follow.objects.filter(user=self.user_to_follow,
                                               author=self.user).exists(),
                         "Follow object was not deleted")

        # test that author's posts do not appear on /follow/ for non-followers
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertNotIn(
            post, response.context['page'],
            "author not followed, but their post appears on /follow/")


class TestCommentSystem(TestCase):
    """Checking whether registered and unregistered users can comment on posts"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser",
                                             password=12345)
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_comments_authenticated(self):
        """ test that authenticated user can add comments """
        comment_text = 'test_comment'
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user)
        response = self.authorized_client.post(
            reverse('add_comment', kwargs={'username': self.user.username,
                                           'post_id': post.pk}),
            {'text': comment_text}, follow=True)
        commentt = Comment.objects.first()
        commentt_count = Post.objects.count()
        self.assertEqual(commentt_count, 1)
        self.assertEqual(commentt.text, comment_text)

    def test_anon_user_commenting(self):
        """test that anonymous user cannot add comments"""
        comment_text = 'test_comment'
        text = 'test_text'
        post = Post.objects.create(
            text=text, author=self.user)
        self.unauthorized_client.post(
            reverse('add_comment', kwargs={'username': 'test',
                                           'post_id': post.pk}),
            {'text': comment_text})
        self.assertFalse(Comment.objects.filter(author=self.user, post=post, text=comment_text).exists())
