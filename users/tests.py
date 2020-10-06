from django.test import TestCase
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

'''
# Create your tests here.
class ProfileTest(TestCase):
    def setUp(self):
        # создание тестового клиента — подходящая задача для функции setUp()
        self.client = Client()
        # создаём пользователя
        self.user = User.objects.create_user(
            username="sarah", email="connor.s@skynet.com", password="12345"
        )
        # создаём пост от имени пользователя
        self.post = Post.objects.create(
            text="You're talking about things I haven't done yet in the past tense. It's driving me crazy!",
            author=self.user)

    def test_profile(self):
        # формируем GET-запрос к странице сайта
        response = self.client.get("/sarah/")

        # проверяем что страница найдена
        self.assertEqual(response.status_code, 200)

        # проверяем, что при отрисовке страницы был получен список из 1 записи
        self.assertEqual(len(response.context["posts"]), 1)

        # проверяем, что объект пользователя, переданный в шаблон,
        # соответствует пользователю, которого мы создали
        self.assertIsInstance(response.context["profile"], User)
        self.assertEqual(response.context["profile"].username, self.user.username)
'''