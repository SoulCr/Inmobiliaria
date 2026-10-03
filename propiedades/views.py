from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .forms import ConsultaForm
from .models import Propiedad
from django.conf import settings
from django.core.mail import send_mail
from django.core.paginator import Paginator




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
            consulta = form.save(commit=False)
            consulta.propiedad = propiedad
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
            consulta.save()
            messages.success(request, "¡Gracias! Recibimos tu consulta y te vamos a responder a la brevedad.")
            return redirect("propiedades:detalle", pk=propiedad.pk)
    else:
        form = ConsultaForm()

    return render(request, "propiedades/detalle.html", {"propiedad": propiedad, "form": form})