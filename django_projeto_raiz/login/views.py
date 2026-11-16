from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages

from .forms import CadastroForm
from .models import Perfil


def eh_administrador(user):
    if user.is_superuser or user.is_staff:
        return True
    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    return perfil.tipo_usuario == "administrador"


class EntrarView(LoginView):
    """Login: admin vai para o painel do Django, cliente vai para o Dashboard."""

    template_name = "login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        destino = self.get_redirect_url()
        if destino:
            return destino
        if eh_administrador(self.request.user):
            return reverse("admin:index")
        return reverse("dashboard")


@login_required
def dashboard(request):
    if eh_administrador(request.user):
        return redirect("admin:index")
    return render(request, "dashboard.html")


@login_required
def perfil(request):
    if request.method == "POST":
        usuario = request.user
        usuario.first_name = request.POST.get("nome", "").strip()
        usuario.last_name = request.POST.get("sobrenome", "").strip()
        usuario.email = request.POST.get("email", "").strip()
        usuario.save()
        messages.success(request, "Dados atualizados.")
        return redirect("perfil")
    return render(request, "perfil.html")


def cadastro(request):
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()  # o Perfil (cliente) é criado pelo signal
        messages.success(request, "Conta criada! Entre com seu usuário e senha.")
        return redirect("login")
    return render(request, "cadastro.html", {"form": form})
