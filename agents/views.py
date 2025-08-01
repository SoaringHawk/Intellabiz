from django.shortcuts import render, get_object_or_404
from .models import Agent  
from django.core.paginator import Paginator
from .forms import AgentForm
from .models import Agent, Workflow
from django.contrib.auth.decorators import login_required
import logging
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .models import Conversation, Message
import json
from django.conf import settings
import google.generativeai as genai
import requests
import threading
import subprocess
import stripe
import threading
import io
import sys
import docker
from django.utils import timezone
from accounts.models import UserProfile


genai.configure(api_key=settings.GEMINI_API_KEY)
stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

# Create your views here.
def home(request):
    context = {
        'MEDIA_URL': settings.MEDIA_URL,
        # other context variables
    }
    return render(request, 'agents/index.html', context)

@login_required(login_url='log_in')
def get_started(request):
    # Check if the user has an agent, or create one
    agent = Agent.objects.filter(user=request.user).first()
    
    if not agent:
        # Create a default agent if none exist
        agent = Agent.objects.create(
            user=request.user,
            name="Intellabiz",
            description="This is your first default agent.",
            # Add other necessary fields for the agent model
        )
        
        # Create a conversation for the new agent
        Conversation.objects.create(
            user=request.user,
            agent=agent,
        )
    
    # Redirect the user to the agent page
    return redirect('agent', pk=agent.pk)


def agent(request, pk):
    # Fetch the agent object using the primary key
    agent = get_object_or_404(Agent, pk=pk)
    
    # Fetch the conversation for this agent
    conversation = Conversation.objects.filter(agent=agent).first()
    
    return render(request, 'agents/agent.html', {
        'agent': agent,
        'MEDIA_URL': settings.MEDIA_URL,
        'conversation_id': str(conversation.id) if conversation else None
    })

@login_required
def get_agent_history(request):
    # Fetch all agents for the current user
    user_agents = Agent.objects.filter(user=request.user).prefetch_related('history')

    # Prepare data to return as JSON
    agents_data = []
    for agent in user_agents:
        conversations = [
            {"title": conversation.title, "timestamp": conversation.timestamp}
            for conversation in agent.history.all()
        ]
        agents_data.append({
            "id": agent.id,
            "name": agent.name,
            "conversations": conversations,
        })

    return JsonResponse({"agents": agents_data})
    
def agents(request):
    return render(request, 'agents/agents.html')

# def agent_list(request):
#     agents = Agent.objects.order_by('id')
#     print(f"Total agents: {agents.count()}")
    
    
#     return render(request, 'agents/agent.html', {'agents': agents})

@login_required
def create_agent(request):
    if request.method == 'POST':
        form = AgentForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.user = request.user
            agent.workflow = None  # Example: default workflow
            agent.save()

            # Create a new conversation for the agent when it is first created
            conversation = Conversation.objects.create(user=request.user, agent=agent)

            # Return the agent ID and the conversation ID (UUID)
            return JsonResponse({'success': True, 'agent_id': agent.pk, 'conversation_id': str(conversation.id)})
        else:
            # If the form is invalid, send the errors back
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = AgentForm()

    return render(request, 'index.html', {'form': form})

@login_required
def get_conversation_data(request, conversation_id):
    print("the convo: ")
    print(conversation_id)
    conversation = get_object_or_404(Conversation, id=conversation_id)
    messages = conversation.messages.all().order_by('timestamp')

    chat_data = [
        {
            'sender': msg.sender_user.username if msg.sender_user else f"Agent {msg.sender_agent.id}",
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M'),
            'is_ai': msg.sender_agent is not None
        } for msg in messages
    ]

    return JsonResponse(chat_data, safe=False)

@csrf_exempt
@login_required
def send_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content')
            conversation_id = data.get('conversation_id')
            
            print(content)
            print(conversation_id)
            
            # Fetch the existing conversation
            conversation = get_object_or_404(Conversation, id=conversation_id)
            
            # Get conversation history
            conversation_history = conversation.messages.all().order_by('timestamp')
            
            # Save the user's message
            user_message = Message.objects.create(sender_user=request.user, content=content)
            conversation.add_message(user_message)
            
            # Call the AI with conversation history
            ai_response = call_gemini_api(content, conversation_history)
            print(ai_response)
            
            # Save the AI response message
            ai_message = Message.objects.create(sender_agent=conversation.agent, content=ai_response)
            conversation.add_message(ai_message)
            
            # Extract code snippets and handle them based on their type
            code_snippets = extract_code_snippets(ai_response)
            workflow_modified = False
            
            for language, code_snippet in code_snippets:
                workflow_modified = True
                if language == 'bash':
                    if conversation.agent.workflow:
                        # Append or replace the Bash command
                        conversation.agent.workflow.append_bash_command(code_snippet)
                    else:
                        # Create a new workflow with Bash
                        workflow = Workflow.objects.create(
                            name='Generated by Gemini',
                            bash_command=code_snippet
                        )
                        conversation.agent.workflow = workflow
                        conversation.agent.save()
                elif language == 'python':
                    if conversation.agent.workflow:
                        # Append or replace the Python code
                        conversation.agent.workflow.append_python_code(code_snippet)
                    else:
                        # Create a new workflow with Python
                        workflow = Workflow.objects.create(
                            name='Generated by Gemini',
                            python_code_snippet=code_snippet
                        )
                        conversation.agent.workflow = workflow
                        conversation.agent.save()
            
            # Return both user and AI messages, along with workflow status
            return JsonResponse({
                'user_message': {
                    'sender': request.user.username,
                    'content': content,
                    'timestamp': user_message.timestamp.strftime('%Y-%m-%d %H:%M')
                },
                'ai_message': {
                    'sender': 'Gemini AI',
                    'content': ai_response,
                    'timestamp': ai_message.timestamp.strftime('%Y-%m-%d %H:%M')
                },
                'workflow_status': 'Workflow created or updated' if workflow_modified else 'No workflow change'
            })
            
        except Exception as e:
            print(f"Error in send_message: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

    
def extract_code_snippets(text):
    """Extracts code snippets enclosed in triple backticks and identifies the language."""
    import re
    # Match the language name and the content inside the triple backticks
    return re.findall(r'```(\w+)?\n(.*?)```', text, re.DOTALL)
# Function to call Google's Gemini API (LLM)

def call_gemini_api(user_input, conversation_history=None):
    try:
        # Create the model
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Initialize chat with history
        chat = model.start_chat(history=[])
        
        # Add conversation history if it exists
        if conversation_history:
            for msg in conversation_history:
                if msg.sender_agent:
                    chat.history.append({
                        "role": "model",
                        "parts": [msg.content]
                    })
                else:
                    chat.history.append({
                        "role": "user",
                        "parts": [msg.content]
                    })
        
        # Send message and get response
        response = chat.send_message(user_input)
        
        return response.text if response and response.text else "Sorry, I couldn't process your request at the moment."
    except Exception as e:
        print(f"Error in call_gemini_api: {e}")
        return "Sorry, there was an error processing your request."

# View to start a new conversation and return the UUID
# @csrf_exempt
# def start_conversation(request):
#     if request.method == 'POST':
#         user = request.user

#         # Fetch an agent (for simplicity using the first one, modify as needed)
#         agent = Agent.objects.first()

#         # Create a new conversation
#         conversation = Conversation.objects.create(user=user, agent=agent)

#         # Return the UUID of the conversation
#         return JsonResponse({
#             'conversation_id': str(conversation.id),
#             'message': 'Conversation started successfully.'
#         })

class WorkflowRunner(threading.Thread):
    def __init__(self, agent, conversation):
        super().__init__()
        self.agent = agent
        self.conversation = conversation
        self._stop_event = threading.Event()
        self.docker_client = docker.from_env()
        self.container = None

    def stop(self):
        self._stop_event.set()

    def run(self):
        workflow = self.agent.workflow
        if not workflow:
            return

        # Ensure the container is set up for the agent
        self.ensure_container()

        # Run the Bash command if it exists
        if workflow.bash_command:
            self.run_bash(workflow.bash_command)

        # Run the Python code if it exists
        if workflow.python_code_snippet:
            self.run_python(workflow.python_code_snippet)

    def ensure_container(self):
        """Create or fetch the Docker container for the agent."""
        if self.agent.container_id:
            # Try to fetch the existing container
            try:
                self.container = self.docker_client.containers.get(self.agent.container_id)
                return
            except docker.errors.NotFound:
                print(f"Container {self.agent.container_id} not found. Creating a new one.")
        
        # Create a new container
        try:
            self.container = self.docker_client.containers.run(
                image="python:3.10-slim",
                name=f"workflow_container_{self.agent.id}",
                detach=True,
                tty=True,
            )
            # Save the container ID to the agent model
            self.agent.container_id = self.container.id
            self.agent.save()
        except docker.errors.APIError as e:
            print(f"Error creating Docker container: {e}")
            raise

    def run_bash(self, bash_command):
        """Run a Bash command inside the Docker container."""
        try:
            result = self.container.exec_run(f"bash -c '{bash_command}'", stdout=True, stderr=True)
            output = result.output.decode("utf-8")
            if result.exit_code == 0:
                send_message_to_chat(self.conversation, sender_agent=self.agent, message=f"Bash Output: {output}")
            else:
                send_message_to_chat(self.conversation, sender_agent=self.agent, message=f"Bash Error: {output}")
        except Exception as e:
            send_message_to_chat(self.conversation, sender_agent=self.agent, message=f"Error running Bash: {str(e)}")

    def run_python(self, python_code_snippet):
        """Run Python code inside the Docker container."""
        script_path = "/tmp/script.py"
        try:
            # Copy the Python script into the container
            with open("temp_script.py", "w") as f:
                f.write(python_code_snippet)

            with open("temp_script.py", "rb") as f:
                self.container.put_archive("/tmp/", f.read())

            # Execute the script
            result = self.container.exec_run(f"python {script_path}", stdout=True, stderr=True)
            output = result.output.decode("utf-8")

            if result.exit_code == 0:
                send_message_to_chat(self.conversation, sender_agent=self.agent, message=f"Python Output: {output}")
            else:
                send_message_to_chat(self.conversation, sender_agent=self.agent, message=f"Python Error: {output}")
        except Exception as e:
            send_message_to_chat(self.conversation, sender_agent=self.agent, message=f"Error running Python: {str(e)}")

    def cleanup(self):
        """Stop and remove the Docker container."""
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
                self.agent.container_id = None
                self.agent.save()
            except docker.errors.APIError as e:
                print(f"Error cleaning up Docker container: {e}")




# Dictionary to hold running workflows
running_workflows = {}
print(running_workflows)

def send_message_to_chat(conversation, sender_user=None, sender_agent=None, message=""):
    """
    Sends a message to the chat by saving it to the database and linking it to the conversation.
    
    :param conversation: The conversation instance the message belongs to.
    :param sender_user: The user sending the message (optional).
    :param sender_agent: The agent sending the message (optional).
    :param message: The content of the message.
    """
    # Create the message instance and save it
    new_message = Message.objects.create(
        sender_user=sender_user,
        sender_agent=sender_agent,
        content=message,
        timestamp=timezone.now()
    )

    # Add the message to the conversation
    conversation.add_message(new_message)

    # If the sender is an agent, also save the conversation in the agent's history
    if sender_agent:
        sender_agent.add_to_history(conversation)

    return new_message

@csrf_exempt
@login_required
def start_workflow(request, agent_id):
    agent = Agent.objects.get(id=agent_id)
    conversation = Conversation.objects.filter(agent=agent, user=agent.user).first()
    
    # Check if a workflow exists for this agent
    if not agent.workflow:
        return JsonResponse({'success': False, 'error': 'No workflow associated with this agent'}, status=400)

    # Start the workflow if it's not already running
    if agent_id not in running_workflows:
        runner = WorkflowRunner(agent,conversation)
        runner.start()
        running_workflows[agent_id] = runner
        return JsonResponse({'success': True, 'output': f"Workflow started for agent {agent.user.username}."})
    
    return JsonResponse({'success': False, 'error': 'Workflow is already running'}, status=400)

@csrf_exempt
@login_required
def stop_workflow(request, agent_id):
    agent = Agent.objects.get(id=agent_id)

    # Stop the workflow if it's running
    if agent_id in running_workflows:
        runner = running_workflows[agent_id]
        runner.stop()
        del running_workflows[agent_id]
        return JsonResponse({'success': True, 'message': f"Workflow stopped for agent {agent.user.username}."})
    
    return JsonResponse({'success': False, 'error': 'No running workflow found'}, status=400)




# @csrf_exempt
# @login_required
# def create_checkout_session(request):
#     if request.method == 'POST':
#         try:
#             print("pass")
#             print(f"User: {request.user}")

#             # Check if the user is authenticated
#             if not request.user.is_authenticated:
#                 return JsonResponse({'error': 'User not authenticated'}, status=403)

#             # Try to get or create the user profile
#             profile, created = UserProfile.objects.get_or_create(user=request.user)
#             if created:
#                 print("UserProfile created for user.")

#             # Parse the request body to get the quantity
#             data = json.loads(request.body)
#             quantity = data.get('quantity', 1)  # Default to 1 if not provided

#             # Define the price in cents (e.g., $0.02 = 2 cents)
#             price_in_cents = 2  # Price for 1 token in cents (2 cents)
#             total_amount = price_in_cents * quantity  # Calculate total amount based on quantity

#             session = stripe.checkout.Session.create(
#                 payment_method_types=['card'],
#                 line_items=[{
#                     'price_data': {
#                         'currency': 'usd',
#                         'product_data': {
#                             'name': f'Token Purchase ({quantity} tokens)',  # Include quantity in the product name
#                         },
#                         'unit_amount': total_amount,  # total amount in cents
#                     },
#                     'quantity': 1,  # Quantity is always 1 in the line item since we're using unit amount
#                 }],
#                 mode='payment',
#                 client_reference_id=request.user.id,  # Pass the user ID as a client reference
#                 success_url='http://127.0.0.1:8000/success?session_id={CHECKOUT_SESSION_ID}',  # Success URL
#                 cancel_url='http://127.0.0.1:8000/cancel',
#             )

#             return JsonResponse({'sessionId': session.id})

#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=403)

# def success_view(request):
#     # Extract session ID from URL params
#     session_id = request.GET.get('session_id', None)

#     if session_id:
#         # Retrieve the session from Stripe
#         session = stripe.checkout.Session.retrieve(session_id)

#         # Ensure the payment is successful
#         if session['payment_status'] == 'paid':
#             user_id = session['client_reference_id']  # Get the user ID from the session
#             user = User.objects.get(id=user_id)
#             profile = UserProfile.objects.get(user=user)

#             # Retrieve the quantity of tokens purchased from the session's line items
#             line_items = stripe.checkout.Session.list_line_items(session_id)
#             quantity = line_items['data'][0]['quantity']  # Get the quantity from the first line item

#             profile.add_tokens(quantity)  # Add tokens based on the purchased quantity

#     return render(request, 'agents/success.html', {'session_id': session_id})

def cancel_view(request):
    return render(request, 'agents/cancel.html')

def buy_token(request):
    return render(request, 'agents/buy_token.html', {
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
    })






@login_required
def create_checkout_session(request):
      # Check if the user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not authenticated'}, status=403)

    # Try to get or create the user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if created:
        print("UserProfile created for user.")
    user_profile = request.user.userprofile

    # Step 1: Create Stripe Customer if not already created
    if not user_profile.stripe_customer_id:
        customer = stripe.Customer.create(
            email=request.user.email,
            name=request.user.username,
        )
        user_profile.stripe_customer_id = customer.id
        user_profile.save()

    # Step 2: Create a Checkout Session for the Subscription
    checkout_session = stripe.checkout.Session.create(
        customer=user_profile.stripe_customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price': 'price_1QBgzSLc6o39q8O0mIn8QNWU',  # Replace with your Stripe Price ID
        }],
        mode='subscription',
        success_url='http://127.0.0.1:8000/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='http://127.0.0.1:8000/cancel',
    )

    # Redirect to Stripe Checkout page where user enters card information
    return redirect(checkout_session.url)


@login_required
def subscription_success(request):
    # Get the session ID from the URL parameters
    session_id = request.GET.get('session_id')

    if session_id:
        # Retrieve the checkout session and the subscription ID from it
        session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = session.subscription

        # Get the user's profile and save the subscription details
        user_profile = request.user.userprofile
        user_profile.stripe_subscription_id = subscription_id

        # Retrieve the subscription to get the subscription item ID
        subscription = stripe.Subscription.retrieve(subscription_id)
        user_profile.stripe_subscription_item_id = subscription['items']['data'][0]['id']
        user_profile.save()

    return render(request, 'success.html')

def pricing(request):
    pricing_plans = [
        {
            'id': 1,
            'name': 'Basic',
            'price': '29',
            'billing_period': 'Per Month',
            'features': [
                {'name': 'Video Duration', 'included': True, 'value': '1-Min Max Duration'},
                {'name': 'Video Templates', 'included': True, 'value': '400+'},
                {'name': 'Stock Elements', 'included': False},
                # Add more features
            ]
        },
        # Add more plans
    ]
    
    comparison_features = [
        {'name': 'Video Duration', 'type': 'text', 'values': ['1-Min Max', '5-Min Max', '20-Min Max', '60-Min Max']},
        {'name': 'Video Templates', 'type': 'text', 'values': ['400+', '400+', '400+', '400+']},
        {'name': 'Stock Elements', 'type': 'boolean', 'values': [False, False, True, True]},
        # Add more comparison features
    ]
    
    context = {
        'pricing_plans': pricing_plans,
        'comparison_features': comparison_features,
    }
    
    return render(request, 'agents/pricing.html', context)

def privacy_policy(request):
    return render(request, 'agents/privacy_policy.html', {
        'MEDIA_URL': settings.MEDIA_URL,
    })

def terms_policy(request):
    return render(request, 'agents/term-policy.html', {
        'MEDIA_URL': settings.MEDIA_URL,
    })

def help_faq(request):
    # You could add FAQ data to the context if you want to make it dynamic
    faq_items = [
        {
            'id': 'One',
            'question': 'What is Intellabiz?',
            'answer': 'Intellabiz is an AI-driven messaging platform that adeptly communicates with users using natural language understanding.'
        },
        # Add more FAQ items as needed
    ]
    
    return render(request, 'agents/help.html', {
        'MEDIA_URL': settings.MEDIA_URL,
        'faq_items': faq_items
    })

def contact(request):
    if request.method == 'POST':
        # Handle form submission here
        # You might want to add email sending functionality
        pass
    
    return render(request, 'agents/contact.html', {
        'MEDIA_URL': settings.MEDIA_URL,
    })