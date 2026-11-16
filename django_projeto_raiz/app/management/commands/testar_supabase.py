from django.core.management.base import BaseCommand

from app.supabase_client import get_supabase


class Command(BaseCommand):
    help = "Testa leitura, cadastro, edição e exclusão na tabela 'integrantes' do Supabase."

    def handle(self, *args, **opcoes):
        try:
            tabela = get_supabase().table("integrantes")
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Não conectou: {exc}"))
            return

        def passo(nome, funcao):
            try:
                resposta = funcao()
                if resposta is not None and not resposta.data:
                    self.stdout.write(self.style.ERROR(f"[FALHOU] {nome}: nenhuma linha afetada (RLS bloqueando?)"))
                    return None
                self.stdout.write(self.style.SUCCESS(f"[OK]     {nome}"))
                return resposta
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"[FALHOU] {nome}: {str(exc)[:220]}"))
                return None

        try:
            tabela.select("*").limit(1).execute()
            self.stdout.write(self.style.SUCCESS("[OK]     ler (select)"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"[FALHOU] ler (select): {str(exc)[:220]}"))
            return

        criado = passo("cadastrar (insert)", lambda: tabela.insert(
            {"nome": "__teste__", "cargo": "teste", "biografia": "teste", "foto_url": ""}).execute())
        if not criado:
            return
        id_teste = criado.data[0]["id"]
        passo("editar (update)", lambda: tabela.update({"cargo": "teste 2"}).eq("id", id_teste).execute())
        passo("excluir (delete)", lambda: tabela.delete().eq("id", id_teste).execute())
        self.stdout.write("Fim do teste. A linha '__teste__' é removida no final.")
