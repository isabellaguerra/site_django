from django.apps.registry import Apps
from django.db import migrations, models


def criar_tabela_se_nao_existir(apps, schema_editor):
    """Cria contato_contato só se ela ainda não existir.

    Em bancos antigos a tabela já veio do antigo app "contato" (nada a fazer).
    Em bancos novos ela é criada aqui.
    """
    if "contato_contato" in schema_editor.connection.introspection.table_names():
        return

    class Contato(models.Model):
        nome = models.CharField(max_length=100)
        email = models.EmailField()
        telefone = models.CharField(max_length=20, blank=True)
        mensagem = models.TextField()

        class Meta:
            app_label = "app"
            db_table = "contato_contato"
            apps = Apps()

    schema_editor.create_model(Contato)


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0002_servico_imagem"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Contato",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("nome", models.CharField(max_length=100)),
                        ("email", models.EmailField(max_length=254)),
                        ("telefone", models.CharField(blank=True, max_length=20)),
                        ("mensagem", models.TextField()),
                    ],
                    options={"db_table": "contato_contato"},
                ),
            ],
            database_operations=[
                migrations.RunPython(criar_tabela_se_nao_existir, migrations.RunPython.noop),
            ],
        ),
    ]
