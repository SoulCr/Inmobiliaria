from django.db import models


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