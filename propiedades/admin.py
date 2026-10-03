from django.contrib import admin
from .models import Consulta, Propiedad, FotoPropiedad


class FotoInline(admin.TabularInline):
    model = FotoPropiedad
    extra = 3

@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "operacion", "moneda", "precio", "zona", "disponible")
    list_filter = ("tipo", "operacion", "disponible")
    search_fields = ("titulo", "zona", "direccion")
    inlines = [FotoInline]


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "propiedad", "email", "telefono", "creada", "atendida")
    list_filter = ("atendida", "creada")
    search_fields = ("nombre", "email", "propiedad__titulo")
    readonly_fields = ("creada",)

