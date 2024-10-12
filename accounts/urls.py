from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('sign-up/', views.sign_up, name='sign_up'),
    path('log-in/', views.log_in, name='log_in'),
    path('log-out/', views.log_out, name='log_out'),
     path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/registration/password_reset_email.html'
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]
