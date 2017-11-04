from django.db import models

class LinkModel(models.Model):
    description = models.TextField(null=True, blank=True)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey('users.UserModel', null=True)
