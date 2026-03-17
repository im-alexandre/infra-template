from django.db import models


class DeploymentNote(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.message
