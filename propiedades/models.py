from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models
from PIL import Image, ImageOps

LADO_MAXIMO = 1600  # las fotos subidas se reducen a este tamaño (en píxeles) para ahorrar espacio


def reducir_imagen(campo, lado_maximo=LADO_MAXIMO):
    """
    Reduce y comprime una foto recién subida (las del celular suelen pesar varios MB).
    Solo actúa cuando se sube un archivo nuevo; si no hay foto nueva, no hace nada.
    """
    if not campo or getattr(campo, "_committed", True):
        return
    try:
        campo.file.seek(0)
        imagen = ImageOps.exif_transpose(Image.open(campo.file))
    except Exception:
        return  # si no se puede leer, se guarda tal cual y que decida la validación de Django
    imagen.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)
    if imagen.mode in ("RGBA", "LA", "P"):
        imagen = imagen.convert("RGBA")
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.split()[-1])
        imagen = fondo
    else:
        imagen = imagen.convert("RGB")
    salida = BytesIO()
    imagen.save(salida, "JPEG", quality=85, optimize=True)
    campo.save(Path(campo.name).stem + ".jpg", ContentFile(salida.getvalue()), save=False)


class Propiedad(models.Model):
    TIPOS = [
        ("casa", "Casa"),
        ("departamento", "Departamento"),
        ("terreno", "Terreno"),
        ("local", "Local"),
    ]
    OPERACIONES = [("venta", "Venta"), ("alquiler", "Alquiler")]
    MONEDAS = [("ARS", "Pesos"), ("USD", "Dólares")]

    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    operacion = models.CharField(max_length=10, choices=OPERACIONES)
    moneda = models.CharField(max_length=3, choices=MONEDAS, default="USD")
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    zona = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True)
    ambientes = models.PositiveSmallIntegerField(null=True, blank=True)
    metros_cuadrados = models.PositiveIntegerField(null=True, blank=True)
    foto = models.ImageField(upload_to="propiedades/", blank=True)
    disponible = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "propiedades"
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.titulo} ({self.get_operacion_display()})"

    def save(self, *args, **kwargs):
        reducir_imagen(self.foto)
        super().save(*args, **kwargs)


class Consulta(models.Model):
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name="consultas")
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True)
    mensaje = models.TextField()
    creada = models.DateTimeField(auto_now_add=True)
    atendida = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.nombre} - {self.propiedad.titulo}"

class FotoPropiedad(models.Model):
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="propiedades/galeria/")
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "foto"
        verbose_name_plural = "fotos"

    def __str__(self):
        return f"Foto de {self.propiedad.titulo}"

    def save(self, *args, **kwargs):
        reducir_imagen(self.imagen)
        super().save(*args, **kwargs)