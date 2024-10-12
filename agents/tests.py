from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Agent, Workflow, Conversation, Message

class AgentViewTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='password123')

        # Create a test workflow
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            code_snippet='print("Hello, World!")'
        )

        # Create a test agent
        self.agent = Agent.objects.create(
            user=self.user,
            workflow=self.workflow
        )

        # Create test messages
        self.message1 = Message.objects.create(
            sender_user=self.user,
            content='Hello, how can I help you?'
        )
        self.message2 = Message.objects.create(
            sender_agent=self.agent,  # Assign the agent as sender
            content='I need assistance with my account.'
        )

        # Create a test conversation
        self.conversation = Conversation.objects.create(
            user=self.user,
            agent=self.agent  # Link to the created agent
        )
        self.conversation.messages.set([self.message1, self.message2])

        # Set up the test client
        self.client = Client()

    def test_agent_view(self):
        # Use the agent's primary key in the URL
        response = self.client.get(reverse('agent', kwargs={'pk': self.agent.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agents/agent.html')
        self.assertContains(response, 'Agent: testuser')
        self.assertContains(response, 'Test Workflow')
        self.assertContains(response, 'Hello, how can I help you?')
        self.assertContains(response, 'I need assistance with my account.')
