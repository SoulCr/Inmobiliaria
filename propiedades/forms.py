from django import forms

from .models import Consulta


class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = ["nombre", "email", "telefono", "mensaje"]
        widgets = {"mensaje": forms.Textarea(attrs={"rows": 4})}