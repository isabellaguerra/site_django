from django import forms

from .models import Contato, Servico


class FormServico(forms.ModelForm):
    ativo = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = Servico
        fields = ("nome", "descricao", "preco", "categoria", "imagem", "ativo")
        widgets = {"descricao": forms.Textarea(attrs={"rows": 5})}


class FormContato(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ("nome", "telefone", "email", "mensagem")
        widgets = {"mensagem": forms.Textarea(attrs={"rows": 7})}
