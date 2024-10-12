from django.db import models
from django.contrib.auth.models import User

# Extend User model with token balance
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tokens = models.IntegerField(default=0)  # Token balance for the user

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def add_tokens(self, amount):
        """Add tokens to the user's balance."""
        self.tokens += amount
        self.save()