"""
Genera el sitio estático y lo sube al repositorio de GitHub de la web pública.
Cloudflare Pages vigila ese repositorio y publica la web solo cuando recibe cambios.

Uso:
    python manage.py publicar_sitio
    python manage.py publicar_sitio --sin-subir    # prepara el commit pero no lo sube

La carpeta del repositorio de la web se toma de SITIO_REPO_DIR (en settings.py).
Si no está definida, se usa una carpeta "inmobiliaria-web" al lado del proyecto.
"""
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

MARCA = ".sitio-generado"
# Si la carpeta elegida tiene alguno de estos, es un proyecto Django y no el repo de la web
CARPETAS_DE_PROYECTO = ("manage.py", "config", "propiedades")


class Command(BaseCommand):
    help = "Genera el sitio estático y lo sube al repositorio de la web pública."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sin-subir", action="store_true",
            help="Hace el commit en la carpeta de la web pero no lo sube a GitHub.",
        )

    # ------------------------------------------------------------------
    def git(self, repo, *args, comprobar=True):
        try:
            r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
        except FileNotFoundError:
            raise CommandError("No se encontró Git. Instalalo desde https://git-scm.com y reabrí la terminal.")
        if comprobar and r.returncode != 0:
            raise CommandError(f"git {' '.join(args)} falló:\n{(r.stderr or r.stdout).strip()}")
        return r

    def handle(self, *args, **opciones):
        base = Path(settings.BASE_DIR).resolve()
        repo = Path(getattr(settings, "SITIO_REPO_DIR", base.parent / "inmobiliaria-web")).resolve()

        # --- Controles de seguridad antes de tocar nada ---
        api_url = getattr(settings, "SITIO_API_URL", "")
        if "127.0.0.1" in api_url or "localhost" in api_url:
            raise CommandError(
                "SITIO_API_URL apunta a tu computadora, así que el formulario no funcionaría en la web publicada.\n"
                "Dejala vacía (SITIO_API_URL = \"\") o poné la dirección pública de la API, y volvé a intentar."
            )
        if not repo.is_dir() or not (repo / ".git").exists():
            raise CommandError(
                f"No encontré el repositorio de la web en:\n  {repo}\n"
                "Clonalo con GitHub Desktop (File > Clone repository) en esa carpeta, "
                "o indicá otra en SITIO_REPO_DIR dentro de settings.py."
            )
        if repo == base or repo in base.parents or base in repo.parents:
            raise CommandError("La carpeta de la web tiene que estar fuera de la carpeta del proyecto.")
        if any((repo / nombre).exists() for nombre in CARPETAS_DE_PROYECTO):
            raise CommandError(f"{repo} parece un proyecto Django, no el repositorio de la web. No se toca nada.")

        # --- Traer lo último del repositorio (por si se editó desde otro lado) ---
        tiene_remoto = bool(self.git(repo, "remote", comprobar=False).stdout.strip())
        if tiene_remoto and not opciones["sin_subir"]:
            r = self.git(repo, "pull", "--ff-only", comprobar=False)
            if r.returncode != 0:
                self.stderr.write(self.style.WARNING(
                    "  No se pudo actualizar desde GitHub (se sigue igual):\n  " + (r.stderr or r.stdout).strip()
                ))

        # --- Generar el sitio en una carpeta temporal y copiarlo al repositorio ---
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "sitio"
            call_command("exportar_sitio", destino=str(salida))

            for elemento in repo.iterdir():
                if elemento.name == ".git":
                    continue
                if elemento.is_dir():
                    shutil.rmtree(elemento)
                else:
                    elemento.unlink()
            shutil.copytree(salida, repo, dirs_exist_ok=True)
            (repo / MARCA).unlink(missing_ok=True)   # marca interna: no hace falta publicarla

        # --- Commit y subida ---
        self.git(repo, "add", "-A")
        cambios = [l for l in self.git(repo, "status", "--porcelain").stdout.splitlines() if l.strip()]
        subir = tiene_remoto and not opciones["sin_subir"]

        if cambios:
            nombre = self.git(repo, "config", "user.name", comprobar=False).stdout.strip()
            email = self.git(repo, "config", "user.email", comprobar=False).stdout.strip()
            identidad = [] if (nombre and email) else [
                "-c", "user.name=Publicador del sitio", "-c", "user.email=publicador@inmobiliaria.local",
            ]
            self.git(repo, *identidad, "commit", "-m", f"Publicar sitio {datetime.now():%Y-%m-%d %H:%M}")
        elif not (subir and self._commits_sin_subir(repo)):
            self.stdout.write(self.style.SUCCESS("No hay cambios para publicar: la web ya está al día."))
            return

        if not subir:
            self.stdout.write(self.style.WARNING(
                f"Commit hecho en {repo} ({len(cambios)} archivos cambiados), pero NO se subió a GitHub."
            ))
            return

        self.git(repo, "push")
        if cambios:
            self.stdout.write(self.style.SUCCESS(
                f"Listo: {len(cambios)} archivos actualizados en GitHub.\n"
                "Cloudflare Pages publica la web en uno o dos minutos."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Se subieron cambios que habían quedado pendientes de una vez anterior.\n"
                "Cloudflare Pages publica la web en uno o dos minutos."
            ))

    def _commits_sin_subir(self, repo):
        """Cantidad de commits locales que todavía no están en GitHub."""
        r = self.git(repo, "rev-list", "--count", "@{u}..HEAD", comprobar=False)
        return int(r.stdout.strip() or 0) if r.returncode == 0 else 0