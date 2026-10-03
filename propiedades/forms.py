from django import forms

from .models import Consulta


class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = ["nombre", "email", "telefono", "mensaje"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }