from django.test import TestCase, Client, override_settings
from posts.models import *
from django.conf import settings
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile

# import django.utils.html.escape to account for special characters
# which are escaped by default in template variables
# https://code.djangoproject.com/wiki/AutoEscaping
from django.utils.html import escape
from PIL import Image
import tempfile


class PostsTest(TestCase):
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
        self.client = Client()
        self.user = User.objects.create_user(
            username='sarah', email='connor.s@skynet.com', password='12345')
        self.follower = User.objects.create_user(
            username='T-800', email='terminator@skynet.com', password='illbeback')
        self.post = Post.objects.create(
            text="You're talking about things I haven't done yet in the past tense. It's driving me crazy!",
            author=self.user)
        self.image = self._create_image()
        self.file = self._create_file()

    def tearDown(self):
        self.image.close()


def test_image_upload(self):
    self.client.login(username='sarah', password='12345')
    # add an image to the test post
    response = self.client.post(f'/sarah/{self.post.id}/edit/',
                                {'text': self.post.text, 'image': self.image})

    # test that image successfully uploaded
    self.assertRedirects(response, f'/sarah/{self.post.id}/')

    # check that changes are reflected on home page, author's profile and post page
    for url in ('/', '/sarah/', f'/sarah/{self.post.id}/'):
        response = self.client.get(url)
        self.assertContains(response,
                            "<img",
                            msg_prefix=f'image is not shown in {url}')
