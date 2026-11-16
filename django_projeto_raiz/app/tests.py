from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Contato, Pedido, Servico


def supabase_falso(dados=None):
    """Imita o encadeamento table().select().execute() do cliente Supabase."""
    cliente = MagicMock()
    cadeia = cliente.table.return_value
    for metodo in ("select", "insert", "update", "delete", "eq", "order"):
        getattr(cadeia, metodo).return_value = cadeia
    cadeia.execute.return_value = MagicMock(data=dados if dados is not None else [])
    return cliente


class FluxoPublicoTests(TestCase):
    def test_paginas_publicas_abrem(self):
        with patch("app.views.get_supabase", return_value=supabase_falso([
            {"id": 1, "nome": "Mariana", "cargo": "QA", "biografia": "Qualidade", "foto_url": ""}
        ])):
            for nome in ("index", "quem_somos", "add_contato", "login", "cadastro", "password_reset"):
                resposta = self.client.get(reverse(nome))
                self.assertEqual(resposta.status_code, 200, nome)

    def test_quem_somos_lista_integrantes_do_supabase(self):
        dados = [{"id": 4, "nome": "Mariana", "cargo": "QA", "biografia": "Qualidade", "foto_url": ""}]
        with patch("app.views.get_supabase", return_value=supabase_falso(dados)):
            resposta = self.client.get(reverse("quem_somos"))
        self.assertContains(resposta, "Mariana")

    def test_quem_somos_nao_quebra_se_supabase_falhar(self):
        with patch("app.views.get_supabase", side_effect=RuntimeError("sem .env")):
            resposta = self.client.get(reverse("quem_somos"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Não foi possível consultar")

    def test_contato_sem_login(self):
        resposta = self.client.post(reverse("add_contato"), {
            "nome": "Feliciano", "telefone": "13991234567",
            "email": "f@email.com", "mensagem": "Gostaria de aprender mais.",
        })
        self.assertRedirects(resposta, reverse("add_contato"))
        self.assertEqual(Contato.objects.count(), 1)

    def test_paginas_privadas_exigem_login(self):
        for nome in ("contatos", "servicos", "addServicos", "integrantes", "addIntegrante",
                     "meus_pedidos", "relatorios", "dashboard", "perfil"):
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, 302, nome)
            self.assertIn("/login/", resposta["Location"], nome)


class ProdutosECompraTests(TestCase):
    def setUp(self):
        self.servico = Servico.objects.create(nome="Site", descricao="HTML", preco=Decimal("2000"))
        Servico.objects.create(nome="Oculto", preco=Decimal("10"), ativo=False)
        self.cliente = User.objects.create_user("ana", "ana@email.com", "senha-forte-123")

    def _api_ok(self):
        resposta = MagicMock()
        resposta.json.return_value = [{"title": "Mochila", "description": "x", "price": 109.95, "image": "http://i/1.png"}]
        return patch("app.views.requests.get", return_value=resposta)

    def test_produtos_mostra_locais_ativos_e_api(self):
        with self._api_ok():
            resposta = self.client.get(reverse("produtos"))
        self.assertContains(resposta, "Site")
        self.assertNotContains(resposta, "Oculto")
        self.assertContains(resposta, "Mochila")

    def test_produtos_funciona_com_api_fora_do_ar(self):
        import requests
        with patch("app.views.requests.get", side_effect=requests.ConnectionError):
            resposta = self.client.get(reverse("produtos"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "indisponíveis")

    def test_visitante_nao_compra(self):
        resposta = self.client.post(reverse("comprar", args=[self.servico.id]))
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_cliente_compra_e_ve_pedido(self):
        self.client.login(username="ana", password="senha-forte-123")
        self.client.post(reverse("comprar", args=[self.servico.id]))
        self.assertEqual(Pedido.objects.filter(usuario=self.cliente).count(), 1)
        resposta = self.client.get(reverse("meus_pedidos"))
        self.assertContains(resposta, "Site")
        self.assertContains(resposta, "2000")

    def test_pedido_sobrevive_a_exclusao_do_servico(self):
        self.client.login(username="ana", password="senha-forte-123")
        self.client.post(reverse("comprar", args=[self.servico.id]))
        self.servico.delete()
        resposta = self.client.get(reverse("meus_pedidos"))
        self.assertContains(resposta, "Site")

    def test_compra_por_get_nao_permitida(self):
        self.client.login(username="ana", password="senha-forte-123")
        self.assertEqual(self.client.get(reverse("comprar", args=[self.servico.id])).status_code, 405)


class LoginTests(TestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("ana", "ana@email.com", "senha-forte-123")
        self.admin = User.objects.create_superuser("admin", "a@email.com", "senha-forte-123")

    def test_cadastro_cria_perfil_cliente(self):
        self.client.post(reverse("cadastro"), {
            "username": "novo", "email": "novo@email.com",
            "password1": "uma-senha-bem-forte-9", "password2": "uma-senha-bem-forte-9",
        })
        novo = User.objects.get(username="novo")
        self.assertEqual(novo.perfil.tipo_usuario, "cliente")

    def test_cliente_vai_para_dashboard(self):
        r = self.client.post(reverse("login"), {"username": "ana", "password": "senha-forte-123"})
        self.assertRedirects(r, reverse("dashboard"))
        self.assertContains(self.client.get(reverse("dashboard")), "Olá, ana!")

    def test_admin_vai_para_painel_do_django(self):
        r = self.client.post(reverse("login"), {"username": "admin", "password": "senha-forte-123"})
        self.assertRedirects(r, reverse("admin:index"), fetch_redirect_response=False)

    def test_superusuario_sem_perfil_nao_quebra(self):
        from login.models import Perfil
        Perfil.objects.filter(usuario=self.admin).delete()
        self.client.login(username="admin", password="senha-forte-123")
        r = self.client.get(reverse("dashboard"))
        self.assertRedirects(r, reverse("admin:index"), fetch_redirect_response=False)

    def test_senha_errada(self):
        r = self.client.post(reverse("login"), {"username": "ana", "password": "errada"})
        self.assertContains(r, "incorretos")

    def test_editar_perfil(self):
        self.client.login(username="ana", password="senha-forte-123")
        self.client.post(reverse("perfil"), {"nome": "Ana", "sobrenome": "Silva", "email": "nova@email.com"})
        self.cliente.refresh_from_db()
        self.assertEqual((self.cliente.first_name, self.cliente.email), ("Ana", "nova@email.com"))

    def test_alterar_senha(self):
        self.client.login(username="ana", password="senha-forte-123")
        r = self.client.post(reverse("alterar_senha"), {
            "old_password": "senha-forte-123",
            "new_password1": "outra-senha-forte-77", "new_password2": "outra-senha-forte-77",
        })
        self.assertRedirects(r, reverse("perfil"))

    def test_recuperacao_de_senha_envia_email(self):
        r = self.client.post(reverse("password_reset"), {"email": "ana@email.com"})
        self.assertRedirects(r, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/login/redefinir/", mail.outbox[0].body)


class GestaoTests(TestCase):
    def setUp(self):
        User.objects.create_user("ana", "ana@email.com", "senha-forte-123")
        self.client.login(username="ana", password="senha-forte-123")
        self.cat = Categoria.objects.create(nome="Design")
        self.a = Servico.objects.create(nome="App", preco=Decimal("1000"), categoria=self.cat)
        self.b = Servico.objects.create(nome="Banner", preco=Decimal("2500"), ativo=False)

    def test_filtros_e_estatisticas(self):
        r = self.client.get(reverse("servicos"))
        self.assertContains(r, "App")
        self.assertContains(r, "Banner")
        self.assertEqual(r.context["total_servicos"], 2)
        self.assertEqual(r.context["mais_barato"], Decimal("1000"))
        self.assertEqual(r.context["mais_caro"], Decimal("2500"))
        r = self.client.get(reverse("servicos"), {"preco": "alto"})
        self.assertEqual([s.nome for s in r.context["servicos"]], ["Banner"])
        r = self.client.get(reverse("servicos"), {"busca": "app"})
        self.assertEqual([s.nome for s in r.context["servicos"]], ["App"])
        r = self.client.get(reverse("servicos"), {"categoria": self.cat.id, "ordem": "maior"})
        self.assertEqual([s.nome for s in r.context["servicos"]], ["App"])

    def test_crud_servico(self):
        self.client.post(reverse("addServicos"), {"nome": "Novo", "descricao": "d", "preco": "300.00", "ativo": "on"})
        novo = Servico.objects.get(nome="Novo")
        self.client.post(reverse("editServicos", args=[novo.id]), {"nome": "Novo 2", "descricao": "d", "preco": "350.00"})
        novo.refresh_from_db()
        self.assertEqual((novo.nome, novo.preco, novo.ativo), ("Novo 2", Decimal("350.00"), False))
        self.client.post(reverse("delServicos", args=[novo.id]))
        self.assertFalse(Servico.objects.filter(id=novo.id).exists())

    def test_excluir_exige_post(self):
        self.assertEqual(self.client.get(reverse("delServicos", args=[self.a.id])).status_code, 405)

    def test_contatos_listar_e_excluir(self):
        c = Contato.objects.create(nome="Feliciano", email="f@email.com", mensagem="Oi")
        self.assertContains(self.client.get(reverse("contatos")), "Feliciano")
        self.client.post(reverse("del_contato", args=[c.id]))
        self.assertEqual(Contato.objects.count(), 0)

    def test_relatorios(self):
        r = self.client.get(reverse("relatorios"))
        self.assertEqual(r.context["servicos_ativos"], 1)
        self.assertEqual(r.context["servicos_inativos"], 1)
        self.assertContains(r, "graficoCategorias")

    def test_equipe_supabase_crud(self):
        falso = supabase_falso([{"id": 4, "nome": "Mariana", "cargo": "QA", "biografia": "b", "foto_url": "http://x/y.png"}])
        with patch("app.views.get_supabase", return_value=falso):
            self.assertContains(self.client.get(reverse("integrantes")), "Mariana")
            self.assertContains(self.client.get(reverse("editIntegrante", args=[4])), "Salvar Alterações")
            self.client.post(reverse("addIntegrante"), {"nome": "N", "cargo": "C", "biografia": "B", "foto": ""})
            falso.table.return_value.insert.assert_called_once()
            self.client.post(reverse("editIntegrante", args=[4]), {"nome": "M2", "cargo": "QA", "biografia": "b", "foto": ""})
            falso.table.return_value.update.assert_called_once()
            self.client.post(reverse("delIntegrante", args=[4]))
            falso.table.return_value.delete.assert_called_once()

    def test_api_categorias(self):
        r = self.client.post("/categoria-api/", {"nome": "Web"}, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        r = self.client.put(f"/categoria-api/{r.json()['id']}", {"nome": "Web 2"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/categoria-api/999").status_code, 404)

    def test_supabase_bloqueando_gravacao_mostra_erro_em_vez_de_sucesso(self):
        """Com RLS, update/delete voltam vazios sem erro: o site não pode dizer 'salvo'."""
        falso = supabase_falso([])
        with patch("app.views.get_supabase", return_value=falso):
            r = self.client.post(reverse("addIntegrante"), {"nome": "N", "cargo": "C", "biografia": "B", "foto": ""})
            self.assertContains(r, "não alterou nenhum registro")
            r = self.client.post(reverse("editIntegrante", args=[4]), {"nome": "M", "cargo": "C", "biografia": "B", "foto": ""})
            self.assertContains(r, "não alterou nenhum registro")
            r = self.client.post(reverse("delIntegrante", args=[4]), follow=True)
            self.assertContains(r, "não alterou nenhum registro")

    def test_erro_de_rls_do_supabase_e_explicado(self):
        falso = supabase_falso([])
        falso.table.return_value.execute.side_effect = Exception(
            "{'code': '42501', 'message': 'new row violates row-level security policy'}")
        with patch("app.views.get_supabase", return_value=falso):
            r = self.client.post(reverse("addIntegrante"), {"nome": "N", "cargo": "C", "biografia": "B", "foto": ""})
        self.assertContains(r, "bloqueou a gravação")
