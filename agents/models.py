from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Workflow(models.Model):
    name = models.CharField(max_length=255)  # Workflow name
    bash_command = models.TextField(blank=True, null=True)  # Field to store the Bash command
    python_code_snippet = models.TextField(blank=True, null=True)  # Field to store the Python code snippet

    def __str__(self):
        return self.name

    def append_bash_command(self, new_bash_command):
        """Append new bash command to the existing bash code."""
        self.bash_command = f'{self.bash_command}\n{new_bash_command}' if self.bash_command else new_bash_command
        self.save()

    def append_python_code(self, new_python_code):
        """Append new Python code to the existing code snippet."""
        self.python_code_snippet = f'{self.python_code_snippet}\n{new_python_code}' if self.python_code_snippet else new_python_code
        self.save()

# Model for a chat message (conversation history)
class Message(models.Model):
    sender_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # User sender
    sender_agent = models.ForeignKey('Agent', on_delete=models.CASCADE, null=True, blank=True)  # Agent sender
    content = models.TextField()  # The content of the message
    timestamp = models.DateTimeField(auto_now_add=True)  # When the message was sent

    def __str__(self):
        sender = self.sender_user.username if self.sender_user else f"Agent {self.sender_agent.id}"
        return f"Message from {sender} at {self.timestamp}"

# Model for chat conversation between a User and an Agent
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # The user involved in the conversation
    agent = models.ForeignKey('Agent', on_delete=models.CASCADE)  # The agent involved in the conversation
    messages = models.ManyToManyField(Message)  # Messages exchanged in the conversation
    started_at = models.DateTimeField(auto_now_add=True)  # When the conversation started

    def __str__(self):
        return f"Conversation between {self.user.username} and Agent {self.agent.id} started at {self.started_at}"

    def add_message(self, message):
        """Add a message to the conversation."""
        self.messages.add(message)

class Agent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agents')
    name = models.CharField(max_length=100, default="Intellabiz")
    workflow = models.OneToOneField(Workflow, on_delete=models.SET_NULL, null=True, blank=True)
    history = models.ManyToManyField(Conversation, blank=True, related_name='agent_conversations')
    description = models.TextField(null=True, blank=True)
    container_id = models.CharField(max_length=255, null=True, blank=True)  # Add container ID field

    def __str__(self):
        return f"Agent: {self.name} - {self.id}"

    def add_to_history(self, conversation):
        """Add a conversation to the agent's history."""
        self.history.add(conversation)
