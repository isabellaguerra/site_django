from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("", views.EntrarView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path(
        "alterar-senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="alterar_senha.html", success_url=reverse_lazy("perfil")
        ),
        name="alterar_senha",
    ),

    # Recuperação de senha: mecanismo nativo do Django (telas padrão do admin)
    path("esqueci-senha/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("esqueci-senha/enviado/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("redefinir/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("redefinir/concluido/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
