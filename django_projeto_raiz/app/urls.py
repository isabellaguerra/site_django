from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("quem-somos/", views.quem_somos, name="quem_somos"),

    # Produtos e compras
    path("produtos", views.produtos, name="produtos"),
    path("comprar/<int:id_servico>/", views.comprar, name="comprar"),
    path("meus-pedidos/", views.meus_pedidos, name="meus_pedidos"),

    # Contato
    path("contato/add-contato/", views.add_contato, name="add_contato"),
    path("contato/contatos/", views.contatos, name="contatos"),
    path("contato/del-contato/<int:id_contato>/", views.del_contato, name="del_contato"),

    # Serviços (CRUD)
    path("servicos", views.servicos, name="servicos"),
    path("add-servicos", views.addServicos, name="addServicos"),
    path("edit-servicos/<int:id_servico>", views.editServicos, name="editServicos"),
    path("del-servicos/<int:id_servico>", views.delServicos, name="delServicos"),

    # Equipe (Supabase)
    path("integrantes", views.integrantes, name="integrantes"),
    path("add-integrante", views.addIntegrante, name="addIntegrante"),
    path("edit-integrante/<int:id_integrante>", views.editIntegrante, name="editIntegrante"),
    path("del-integrante/<int:id_integrante>", views.delIntegrante, name="delIntegrante"),

    path("relatorios/", views.relatorios, name="relatorios"),

    # API REST de categorias
    path("categoria-api/", views.categoriasAPI, name="categoriasAPI"),
    path("categoria-api/<int:id_categoria>", views.categoriaAPI, name="categoriaAPI"),
]
