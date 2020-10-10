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

    def test_edit_post_authenticated(self):
        self.post = Post.objects.create(text=self.text, author=self.user)
        response = self.authorized_client.get(f'/username/{self.post.id}/edit/')
        self.assertEqual(response.status_code, 200, 'Let s check access to the editing page for an authorized user')
        # Edit the post and check for changes in the database
        first_text = self.post.text
        new_text = "Checking text in the database"
        self.authorized_client.post(f'/username/{self.post.id}/edit/', {'text': new_text})
        # Updating the post in the database
        self.post.refresh_from_db()
        self.assertEqual(first_text, new_text)
        # Let s see if the data on the pages has changed
        urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': 'username', 'post_id': self.post.pk})]
        for url in urls:
            response = self.authorized_client.get(url)
            self.assertContains(response,
                                escape(first_text),
                                msg_prefix=f'Nothing was updated in {url}')
            # Let's check that the entry was edited and there is no new one
            self.assertNotContains(response,
                                   escape(first_text),
                                   msg_prefix=f'The old post still remains in {url}')

    def test_change_the_group(self):  # ~3 часа потратил, ничего другого не могу придумать, не карайте =)
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
        self.assertEqual(post_edited.text, text_edited)
        self.assertEqual(post_edited.group, leo)
        self.assertEqual(post_count, 1)

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
        non_image_path = 'posts/tests.py'
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
        self.unauthorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.text = 'test_text'

    def test_index_cache(self):
        # Creating the page cache and checking that the new post has not yet appeared
        self.authorized_client.get(reverse('index'))
        self.authorized_client.post(reverse('new_post'), {'text': self.text})
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, self.text)
        self.assertNotContains(
            response,
            'test_text',
            msg_prefix="The home page is not cached")
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

    def test_follow(self):
        """ test following, unfollowing and accessing followed authors' posts """
        # test following
        response = self.authorized_client.get('/Test_profile_for_the_subscription/')
        self.assertContains(response, 'href="/Test_profile_for_the_subscription/follow"',
                            msg_prefix='"Follow" button not found on profile page')
        self.assertNotContains(response, 'href="/Test_profile_for_the_subscription/unfollow"',
                               msg_prefix='"Unfollow" button found on profile page')
        response = self.authorized_client.get('/Test_profile_for_the_subscription/follow')
        self.assertTrue(
            Follow.objects.filter(user=self.follower, author=self.user).exists(),
            "Follow object was not created")

        # test that follower can see followed author's post
        response = self.authorized_client.get('/follow/')
        self.assertIn(
            self.post, response.context['page'],
            "follower can not see their subscriptions on /follow/ page")

        # test unfollowing
        response = self.authorized_client.get('/Test_profile_for_the_subscription/')
        self.assertNotContains(response, 'href="/Test_profile_for_the_subscription/follow"',
                               msg_prefix='"Follow" button found on profile page')
        self.assertContains(response, 'href="/Test_profile_for_the_subscription/unfollow"',
                            msg_prefix='"Unfollow" button not found on profile page')
        response = self.authorized_client.get('/Test_profile_for_the_subscription/unfollow')
        self.assertFalse(Follow.objects.filter(user=self.follower, author=self.user).exists(),
                         "Follow object was not deleted")

        # test that author's posts do not appear on /follow/ for non-followers
        response = self.authorized_client.get('/follow/')
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

# Тесты первых спринтов поправил, их проверяли другие ревьюеры, надеюсь что сейчас всё норм.
# Последние тесты переписал, точнее исправил.
# Очень много времени потратил на все тесты, надеюсь вам получилось хорошо и вам понравилось =)
# Да и в целом постарался исправить ваши замечания во всём коде кроме моделей, там одно из имён я поменял частично.
# В файле post.html пасхалка, понимаю что код пасхалки работает не корректно, но увидеть пасхалку всегда приятно =)
# Ни удивляйтесь что я отправляю проверку ночью, мне хочется как можно скорее закрыть проект в практикуме, чтобы заняться основными делами.

# Спасибо за быстрые и классные проверки =)
# Надеюсь на этот раз не много ошибок)
