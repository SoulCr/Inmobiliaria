"""
Genera la versión pública del sitio como archivos estáticos (HTML + imágenes
optimizadas) en la carpeta dist/, lista para subir a Cloudflare Pages.

Uso:
    python manage.py exportar_sitio
    python manage.py exportar_sitio --destino C:\\ruta\\otra_carpeta
"""
import hashlib
import io
import shutil
import unicodedata
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from PIL import Image, ImageOps

from propiedades.models import Propiedad

ANCHO_TARJETA = 640    # miniatura para el listado
ANCHO_DETALLE = 1280   # foto grande para el detalle
MARCA = ".sitio-generado"  # evita borrar por error una carpeta que no es de salida


def normalizar(texto):
    """Minúsculas y sin acentos, para filtrar por zona sin importar tildes."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )
    return sin_acentos.strip()


class Command(BaseCommand):
    help = "Genera el sitio público estático (HTML + imágenes optimizadas) en dist/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino",
            default=None,
            help="Carpeta de salida (por defecto: dist/ en la raíz del proyecto).",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **opciones):
        base = Path(settings.BASE_DIR).resolve()
        destino = Path(opciones["destino"] or base / "dist").resolve()

        if destino == base or destino in base.parents or destino == Path(destino.anchor):
            raise CommandError(f"Carpeta de salida no permitida: {destino}")
        if destino.exists() and any(destino.iterdir()) and not (destino / MARCA).exists():
            raise CommandError(
                f"{destino} ya tiene archivos que no fueron generados por este comando. "
                "Usá otra carpeta o vaciála a mano."
            )

        if destino.exists():
            shutil.rmtree(destino)
        (destino / "media").mkdir(parents=True)
        (destino / MARCA).write_text("Carpeta generada por exportar_sitio. Se puede regenerar.\n")

        propiedades = list(
            Propiedad.objects.filter(disponible=True).prefetch_related("fotos")
        )
        cantidad_fotos = 0
        for p in propiedades:
            p.zona_norm = normalizar(p.zona)
            imagenes = []
            if p.foto:
                imagenes.append((p.foto, "principal"))
            imagenes += [(f.imagen, f"g{i}") for i, f in enumerate(p.fotos.all(), start=1)]

            p.imagenes = []
            for fichero, etiqueta in imagenes:
                url = self._guardar_imagen(fichero, ANCHO_DETALLE, destino, f"p{p.pk}-{etiqueta}")
                if url:
                    p.imagenes.append(url)
            cantidad_fotos += len(p.imagenes)

            # Miniatura del listado: se genera desde la foto principal (o la primera de la galería)
            origen = p.foto if p.foto else (p.fotos.first().imagen if p.fotos.exists() else None)
            p.card_url = (
                self._guardar_imagen(origen, ANCHO_TARJETA, destino, f"p{p.pk}-card") if origen else None
            )

        api_url = getattr(settings, "SITIO_API_URL", "")

        self._escribir(
            destino / "index.html",
            render_to_string("propiedades/sitio_listado.html", {
                "propiedades": propiedades,
                "total": len(propiedades),
                "tipos": Propiedad.TIPOS,
                "operaciones": Propiedad.OPERACIONES,
            }),
        )
        for p in propiedades:
            self._escribir(
                destino / "propiedad" / str(p.pk) / "index.html",
                render_to_string("propiedades/sitio_detalle.html", {"propiedad": p, "api_url": api_url}),
            )
        self._escribir(destino / "404.html", render_to_string("propiedades/sitio_404.html"))

        # Archivos estáticos del sitio (CSS, logos, favicon)
        estaticos = Path(apps.get_app_config("propiedades").path) / "static" / "propiedades"
        shutil.copytree(
            estaticos,
            destino / "static" / "propiedades",
            ignore=shutil.ignore_patterns("Inmobiliaria_sur.png"),  # original sin uso
        )

        # Caché del navegador (Cloudflare Pages lee este archivo)
        self._escribir(destino / "_headers", (
            "/static/*\n  Cache-Control: public, max-age=3600\n\n"
            "/media/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        ))

        peso = sum(f.stat().st_size for f in destino.rglob("*") if f.is_file()) / 1024 / 1024
        self.stdout.write(self.style.SUCCESS(
            f"Sitio generado en {destino}\n"
            f"  {len(propiedades)} propiedades, {cantidad_fotos} fotos, {peso:.1f} MB en total"
        ))
        if not api_url:
            self.stdout.write(self.style.WARNING(
                "  Aviso: SITIO_API_URL está vacío; las páginas de detalle no mostrarán el formulario de consulta."
            ))

    # ------------------------------------------------------------------
    def _escribir(self, ruta, contenido):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    def _guardar_imagen(self, fichero, ancho, destino, prefijo):
        """Guarda una versión JPEG reducida y devuelve su URL pública (/media/...)."""
        try:
            with fichero.storage.open(fichero.name, "rb") as f:
                datos = f.read()
        except (FileNotFoundError, OSError, ValueError):
            self.stderr.write(self.style.WARNING(f"  No se encontró la imagen {fichero.name}; se omite."))
            return None

        # El nombre lleva una huella del contenido: si cambia la foto, cambia la URL
        huella = hashlib.md5(datos).hexdigest()[:8]
        nombre = f"{prefijo}-{huella}.jpg"
        ruta = destino / "media" / nombre
        if not ruta.exists():
            try:
                imagen = ImageOps.exif_transpose(Image.open(io.BytesIO(datos)))
            except OSError:
                self.stderr.write(self.style.WARNING(f"  {fichero.name} no es una imagen válida; se omite."))
                return None
            if imagen.mode in ("RGBA", "LA", "P"):
                imagen = imagen.convert("RGBA")
                fondo = Image.new("RGB", imagen.size, (255, 255, 255))
                fondo.paste(imagen, mask=imagen.split()[-1])
                imagen = fondo
            else:
                imagen = imagen.convert("RGB")
            imagen.thumbnail((ancho, ancho * 2), Image.LANCZOS)
            imagen.save(ruta, "JPEG", quality=82, optimize=True, progressive=True)
        return f"/media/{nombre}"
