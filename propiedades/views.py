from django.shortcuts import get_object_or_404, render

from .models import Propiedad


def listado(request):
    propiedades = Propiedad.objects.filter(disponible=True)

    tipo = request.GET.get("tipo", "")
    operacion = request.GET.get("operacion", "")
    zona = request.GET.get("zona", "").strip()

    if tipo:
        propiedades = propiedades.filter(tipo=tipo)
    if operacion:
        propiedades = propiedades.filter(operacion=operacion)
    if zona:
        propiedades = propiedades.filter(zona__icontains=zona)

    return render(request, "propiedades/listado.html", {
        "propiedades": propiedades,
        "tipos": Propiedad.TIPOS,
        "operaciones": Propiedad.OPERACIONES,
        "filtros": {"tipo": tipo, "operacion": operacion, "zona": zona},
    })


def detalle(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk, disponible=True)
    return render(request, "propiedades/detalle.html", {"propiedad": propiedad})