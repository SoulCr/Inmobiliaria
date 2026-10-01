from django.contrib import admin
from .models import Propiedad


@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "operacion", "moneda", "precio", "zona", "disponible")
    list_filter = ("tipo", "operacion", "disponible")
    search_fields = ("titulo", "zona", "direccion")