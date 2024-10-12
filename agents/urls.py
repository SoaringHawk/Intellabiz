from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('get-started/', views.get_started, name='get_started'),
    path('agent/<int:pk>/', views.agent, name='agent'),
    # path('agents/', views.agent_list, name='agent_list'),
    path('create-agent/', views.create_agent, name='create_agent'),
    path('get_conversation_data/<int:conversation_id>/', views.get_conversation_data, name='get_conversation_data'),
    path('send_message/', views.send_message, name='send_message'),
    #  path('start_conversation/', views.start_conversation, name='start_conversation'),
    path('start_workflow/<int:agent_id>/', views.start_workflow, name='start_workflow'),
    path('stop_workflow/<int:agent_id>/', views.stop_workflow, name='stop_workflow'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('success/', views.success_view, name='success'),
    path('cancel/', views.cancel_view, name='cancel'),
    path('buy-token/', views.buy_token, name='buy_token'),
    
]
