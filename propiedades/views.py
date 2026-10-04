from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import ConsultaForm
from .models import Propiedad

MAX_MENSAJE = 2000


def registrar_consulta(propiedad, form):
    """Guarda la consulta y avisa por mail. La usan la web y la API."""
    consulta = form.save(commit=False)
    consulta.propiedad = propiedad
    consulta.save()
    try:
        send_mail(
            subject=f"Nueva consulta: {propiedad.titulo}",
            message=(
                f"Propiedad: {propiedad.titulo}\n"
                f"Nombre: {consulta.nombre}\n"
                f"Email: {consulta.email}\n"
                f"Teléfono: {consulta.telefono or '-'}\n\n"
                f"Mensaje:\n{consulta.mensaje}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_INMOBILIARIA],
        )
    except OSError as e:
        print("No se pudo enviar el mail:", e)
    return consulta


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

    paginator = Paginator(propiedades, 9)  # 9 propiedades por página
    pagina = paginator.get_page(request.GET.get("page"))

    # Filtros actuales, sin el número de página, para armar los links
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "propiedades/listado.html", {
        "pagina": pagina,
        "tipos": Propiedad.TIPOS,
        "operaciones": Propiedad.OPERACIONES,
        "filtros": {"tipo": tipo, "operacion": operacion, "zona": zona},
        "querystring": params.urlencode(),
    })


def detalle(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk, disponible=True)

    if request.method == "POST":
        form = ConsultaForm(request.POST)
        if form.is_valid():
            registrar_consulta(propiedad, form)
            messages.success(request, "¡Gracias! Recibimos tu consulta y te vamos a responder a la brevedad.")
            return redirect("propiedades:detalle", pk=propiedad.pk)
    else:
        form = ConsultaForm()

    return render(request, "propiedades/detalle.html", {"propiedad": propiedad, "form": form})


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def api_consulta(request):
    """Recibe las consultas del sitio estático (publicado en otro dominio)."""
    permitidos = getattr(settings, "SITIO_ORIGENES_PERMITIDOS", [])
    origen = request.headers.get("Origin", "")

    # Un navegador que escribe desde un sitio no autorizado no puede enviar consultas
    if origen and origen not in permitidos:
        return JsonResponse({"ok": False, "errores": {"__all__": ["Origen no permitido."]}}, status=403)

    def responder(respuesta):
        if origen:
            respuesta["Access-Control-Allow-Origin"] = origen
            respuesta["Vary"] = "Origin"
        return respuesta

    if request.method == "OPTIONS":
        respuesta = HttpResponse(status=204)
        respuesta["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        respuesta["Access-Control-Allow-Headers"] = "Content-Type"
        respuesta["Access-Control-Max-Age"] = "86400"
        return responder(respuesta)

    # Campo trampa: los bots suelen completarlo. Se responde "ok" sin guardar nada.
    if request.POST.get("web"):
        return responder(JsonResponse({"ok": True}))

    pk = request.POST.get("propiedad", "")
    propiedad = Propiedad.objects.filter(pk=pk, disponible=True).first() if pk.isdigit() else None
    if propiedad is None:
        return responder(JsonResponse(
            {"ok": False, "errores": {"__all__": ["Esa propiedad ya no está disponible."]}}, status=404
        ))

    form = ConsultaForm(request.POST)
    if not form.is_valid():
        errores = {campo: [str(e) for e in lista] for campo, lista in form.errors.items()}
        return responder(JsonResponse({"ok": False, "errores": errores}, status=400))

    if len(form.cleaned_data["mensaje"]) > MAX_MENSAJE:
        return responder(JsonResponse(
            {"ok": False, "errores": {"mensaje": [f"El mensaje es demasiado largo (máximo {MAX_MENSAJE} caracteres)."]}},
            status=400,
        ))

    registrar_consulta(propiedad, form)
    return responder(JsonResponse({"ok": True}))
