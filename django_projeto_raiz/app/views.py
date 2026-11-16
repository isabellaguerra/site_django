from urllib.parse import urlencode

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Min, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .forms import FormContato, FormServico
from .models import Categoria, Contato, Pedido, Servico
from .serializers import CategoriaSerializer
from .supabase_client import get_supabase

API_PRODUTOS_URL = "https://fakestoreapi.com/products"


# ---------------------------------------------------------------- páginas públicas
def index(request):
    return render(request, "index.html")


def _listar_integrantes(request):
    """Busca os integrantes no Supabase. Se falhar, avisa e devolve lista vazia."""
    try:
        resposta = get_supabase().table("integrantes").select("*").order("id").execute()
        return resposta.data or []
    except Exception:
        messages.error(request, "Não foi possível consultar o banco remoto (Supabase) agora.")
        return []


def quem_somos(request):
    return render(request, "quem-somos.html", {"integrantes": _listar_integrantes(request)})


def produtos(request):
    servicos = Servico.objects.filter(ativo=True).order_by("nome")

    try:
        resposta = requests.get(API_PRODUTOS_URL, timeout=8)
        resposta.raise_for_status()
        produtos_api = resposta.json()
    except (requests.RequestException, ValueError):
        produtos_api = []
        messages.warning(request, "Os produtos das lojas parceiras estão indisponíveis no momento.")

    return render(request, "produtos.html", {"servicos": servicos, "produtos_api": produtos_api})


def add_contato(request):
    """Formulário de contato: qualquer visitante pode enviar, sem login."""
    form = FormContato(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mensagem enviada! Responderemos em breve.")
        return redirect("add_contato")
    return render(request, "add-contato.html", {"form": form})


# ---------------------------------------------------------------- compras (logado)
@login_required
@require_POST
def comprar(request, id_servico):
    servico = get_object_or_404(Servico, id=id_servico, ativo=True)
    Pedido.objects.create(
        usuario=request.user, servico=servico, nome=servico.nome, preco=servico.preco
    )
    messages.success(request, f"“{servico.nome}” foi adicionado aos seus pedidos.")
    return redirect("meus_pedidos")


@login_required
def meus_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).select_related("servico")
    total = pedidos.aggregate(total=Sum("preco"))["total"] or 0
    return render(request, "meus-pedidos.html", {"pedidos": pedidos, "total": total})


# ---------------------------------------------------------------- contatos (logado)
@login_required
def contatos(request):
    lista = Contato.objects.all().order_by("-id")
    return render(request, "contatos.html", {"contatos": lista})


@login_required
@require_POST
def del_contato(request, id_contato):
    get_object_or_404(Contato, id=id_contato).delete()
    messages.success(request, "Contato excluído.")
    return redirect("contatos")


# ---------------------------------------------------------------- serviços (logado)
def _url_filtros(params, **mudancas):
    """Monta a query string dos filtros, trocando/removendo só o que mudou."""
    novos = {k: v for k, v in params.items() if v}
    for chave, valor in mudancas.items():
        if valor:
            novos[chave] = valor
        else:
            novos.pop(chave, None)
    return "?" + urlencode(novos) if novos else "?"


@login_required
def servicos(request):
    todos = Servico.objects.select_related("categoria")

    # estatísticas (sobre todos os serviços cadastrados)
    stats = todos.aggregate(menor=Min("preco"), maior=Max("preco"))
    total_servicos = todos.count()
    total_ativos = todos.filter(ativo=True).count()

    busca = request.GET.get("busca", "").strip()
    categoria = request.GET.get("categoria", "")
    preco = request.GET.get("preco", "")
    ordem = request.GET.get("ordem", "")

    lista = todos
    if busca:
        lista = lista.filter(nome__icontains=busca)
    if categoria.isdigit():
        lista = lista.filter(categoria_id=categoria)
    if preco == "baixo":
        lista = lista.filter(preco__lte=500)
    elif preco == "medio":
        lista = lista.filter(preco__gt=500, preco__lte=1500)
    elif preco == "alto":
        lista = lista.filter(preco__gt=1500)

    lista = lista.order_by({"menor": "preco", "maior": "-preco"}.get(ordem, "nome"))

    params = {"busca": busca, "categoria": categoria, "preco": preco, "ordem": ordem}
    contexto = {
        "servicos": lista,
        "total_servicos": total_servicos,
        "total_ativos": total_ativos,
        "mais_barato": stats["menor"],
        "mais_caro": stats["maior"],
        "chips_categoria": [
            {"nome": c.nome, "ativo": categoria == str(c.id), "url": _url_filtros(params, categoria=str(c.id))}
            for c in Categoria.objects.filter(ativo=True)
        ],
        "busca": busca,
        "categoria": categoria,
        "preco": preco,
        "ordem": ordem,
        "url_ordem_menor": _url_filtros(params, ordem="menor"),
        "url_ordem_maior": _url_filtros(params, ordem="maior"),
        "url_ordem_nome": _url_filtros(params, ordem="nome"),
        "url_preco": {
            "baixo": _url_filtros(params, preco="baixo"),
            "medio": _url_filtros(params, preco="medio"),
            "alto": _url_filtros(params, preco="alto"),
        },
    }
    return render(request, "servicos.html", contexto)


@login_required
def addServicos(request):
    form = FormServico(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Serviço cadastrado.")
        return redirect("servicos")
    return render(request, "add-servicos.html", {"form": form})


@login_required
def editServicos(request, id_servico):
    servico = get_object_or_404(Servico, id=id_servico)
    form = FormServico(request.POST or None, request.FILES or None, instance=servico)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Serviço atualizado.")
        return redirect("servicos")
    return render(request, "edit-servicos.html", {"form": form, "servico": servico})


@login_required
@require_POST
def delServicos(request, id_servico):
    get_object_or_404(Servico, id=id_servico).delete()
    messages.success(request, "Serviço excluído.")
    return redirect("servicos")


# ---------------------------------------------------------------- equipe / Supabase (logado)
@login_required
def integrantes(request):
    return render(request, "integrantes.html", {"integrantes": _listar_integrantes(request)})


def _dados_integrante(post):
    return {
        "nome": post.get("nome", "").strip(),
        "cargo": post.get("cargo", "").strip(),
        "biografia": post.get("biografia", "").strip(),
        "foto_url": post.get("foto", "").strip(),
    }


def _explicar_erro(exc):
    """Traduz o erro do Supabase para algo que dê para entender e corrigir."""
    texto = str(exc)
    if "row-level security" in texto or "42501" in texto:
        return ("O Supabase bloqueou a gravação (RLS). Libere insert/update/delete na tabela "
                "'integrantes' — o passo a passo está no LEIA-ME.")
    if "null value in column" in texto and "id" in texto:
        return "A coluna 'id' da tabela 'integrantes' não gera número sozinha (veja o LEIA-ME)."
    return f"Erro do Supabase: {texto[:200]}"


MSG_SEM_EFEITO = ("O Supabase não alterou nenhum registro. Provavelmente a tabela 'integrantes' "
                  "não permite essa operação (RLS) — veja o LEIA-ME.")


@login_required
def addIntegrante(request):
    if request.method == "POST":
        try:
            resposta = get_supabase().table("integrantes").insert(_dados_integrante(request.POST)).execute()
            if not resposta.data:
                raise RuntimeError(MSG_SEM_EFEITO)
            messages.success(request, "Integrante cadastrado.")
            return redirect("integrantes")
        except Exception as exc:
            messages.error(request, _explicar_erro(exc))
    return render(request, "add-integrante.html", {"dados": request.POST})


@login_required
def editIntegrante(request, id_integrante):
    try:
        tabela = get_supabase().table("integrantes")
        if request.method == "POST":
            resposta = tabela.update(_dados_integrante(request.POST)).eq("id", id_integrante).execute()
            if not resposta.data:
                raise RuntimeError(MSG_SEM_EFEITO)
            messages.success(request, "Integrante atualizado.")
            return redirect("integrantes")
        resposta = tabela.select("*").eq("id", id_integrante).execute()
    except Exception as exc:
        messages.error(request, _explicar_erro(exc))
        if request.method == "POST":
            # volta ao formulário mantendo o que a pessoa digitou
            dados = _dados_integrante(request.POST)
            dados.update({"id": id_integrante, "foto_url": dados["foto_url"]})
            return render(request, "edit-integrante.html", {"integrante": dados})
        return redirect("integrantes")

    if not resposta.data:
        messages.error(request, "Integrante não encontrado.")
        return redirect("integrantes")
    return render(request, "edit-integrante.html", {"integrante": resposta.data[0]})


@login_required
@require_POST
def delIntegrante(request, id_integrante):
    try:
        resposta = get_supabase().table("integrantes").delete().eq("id", id_integrante).execute()
        if not resposta.data:
            raise RuntimeError(MSG_SEM_EFEITO)
        messages.success(request, "Integrante excluído.")
    except Exception as exc:
        messages.error(request, _explicar_erro(exc))
    return redirect("integrantes")


# ---------------------------------------------------------------- relatórios (logado)
@login_required
def relatorios(request):
    servicos = Servico.objects.all()
    categorias = servicos.values("categoria__nome").annotate(quantidade=Count("id")).order_by("categoria__nome")

    return render(request, "relatorio.html", {
        "total_servicos": servicos.count(),
        "servicos_ativos": servicos.filter(ativo=True).count(),
        "servicos_inativos": servicos.filter(ativo=False).count(),
        "categorias_labels": [i["categoria__nome"] or "Sem categoria" for i in categorias],
        "categorias_valores": [i["quantidade"] for i in categorias],
    })


# ---------------------------------------------------------------- API REST de categorias
@api_view(["GET", "POST"])
def categoriasAPI(request):
    if request.method == "GET":
        serializer = CategoriaSerializer(Categoria.objects.all(), many=True)
        return Response(serializer.data)

    serializer = CategoriaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "DELETE", "PUT"])
def categoriaAPI(request, id_categoria):
    try:
        categoria = Categoria.objects.get(id=id_categoria)
    except Categoria.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(CategoriaSerializer(categoria).data)

    if request.method == "DELETE":
        categoria.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CategoriaSerializer(categoria, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
