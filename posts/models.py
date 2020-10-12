from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.constraints import UniqueConstraint

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    class Meta:
        ordering = ("-pub_date",)

    text = models.TextField()
    pub_date = models.DateTimeField("date published",
                                    auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="posts")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL,
                              blank=True, null=True, related_name="posts_group")
    image = models.ImageField(upload_to="posts/", blank=True, null=True)

    def __str__(self):
        return self.text


class Comment(models.Model):
    class Meta:
        ordering = ("-created",)

    post = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name="Comment",
                             related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="comments_author")
    text = models.TextField()
    created = models.DateTimeField("date published", auto_now_add=True)


class Follow(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author", ],
                name="unique user-author"
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
