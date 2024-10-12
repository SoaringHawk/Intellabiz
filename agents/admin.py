from django.contrib import admin
from .models import Agent, Workflow, Message, Conversation

# Message admin configuration
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender_user', 'sender_agent', 'content', 'timestamp')  # Columns to display
    search_fields = ('sender_user__username', 'sender_agent__id', 'content')  # Enable search by sender and content
    list_filter = ('timestamp',)  # Filter by timestamp

# Conversation admin configuration
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'agent', 'started_at')  # Display conversation ID
    search_fields = ('user__username', 'agent__id')  # Enable search by user and agent
    list_filter = ('started_at',)  # Filter by the conversation start time
    filter_horizontal = ('messages',)  # Allows easier management of ManyToManyField (messages)

# Register the Agent model with the AgentAdmin class
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'description')  # Columns to display in the admin list view
    search_fields = ('user__username', 'description')  # Enable search by username and description
    list_filter = ('user',)  # Add filter options for users

# Register the Workflow model with the WorkflowAdmin class
@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'bash_command', 'python_code_snippet','id')  # Columns to display in the admin list view
    search_fields = ('name',)  # Enable search by name
    ordering = ('name',)  # Default ordering by name
