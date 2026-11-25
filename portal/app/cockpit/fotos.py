"""Fotodokumentation: Upload vom Handy, Metadaten (EXIF/GPS) entfernen, sicher ablegen.

* Bild wird mit Pillow neu kodiert (JPEG, max. 2400 px) – dabei entfallen EXIF, GPS und eingebettete Daten.
* Ablage unter ``MEDIA_ROOT/fotos/JJJJ/MM/<uuid>.jpg`` (Volume im Betrieb verschlüsselt, siehe SECURITY.md);
  Auslieferung nur über eine geprüfte Ansicht, nie direkt per Webserver.
* Dublettenschutz über SHA-256 (Datenbank-Index).
"""

import hashlib
import io
import uuid
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from dokumente.models import Dokument, Foto

MAX_BYTES = 15 * 1024 * 1024
MAX_KANTE = 2400


class FotoFehler(ValueError):
    pass


def bereinigt(daten: bytes) -> bytes:
    if len(daten) > MAX_BYTES:
        raise FotoFehler("Foto ist größer als 15 MB.")
    try:
        bild = Image.open(io.BytesIO(daten))
        bild = ImageOps.exif_transpose(bild)   # Ausrichtung übernehmen, bevor EXIF entfällt
    except (UnidentifiedImageError, OSError) as e:
        raise FotoFehler("Datei ist kein lesbares Bild.") from e
    bild = bild.convert("RGB")
    bild.thumbnail((MAX_KANTE, MAX_KANTE))
    ziel = io.BytesIO()
    bild.save(ziel, "JPEG", quality=85, optimize=True)   # ohne exif= → keine Metadaten
    return ziel.getvalue()


def speichern(einsatz, datei, typ: str, benutzer, beschreibung: str = "") -> Foto:
    inhalt = bereinigt(datei.read())
    jetzt = timezone.localtime()
    schluessel = f"fotos/{jetzt:%Y/%m}/{uuid.uuid4().hex}.jpg"
    pfad = Path(settings.MEDIA_ROOT) / schluessel
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_bytes(inhalt)
    try:
        with transaction.atomic():
            dok = Dokument.objects.create(dateiname=f"{typ}-{jetzt:%Y%m%d-%H%M%S}.jpg", mime_typ="image/jpeg",
                                          groesse_bytes=len(inhalt), sha256=hashlib.sha256(inhalt).hexdigest(),
                                          speicher_schluessel=schluessel, kategorie="foto", einsatz=einsatz,
                                          hochgeladen_von=benutzer)
            return Foto.objects.create(dokument=dok, einsatz=einsatz, typ=typ, aufgenommen_am=timezone.now(),
                                       beschreibung=beschreibung or None)
    except IntegrityError as e:
        pfad.unlink(missing_ok=True)
        raise FotoFehler("Dieses Foto ist bereits gespeichert.") from e


def datei_pfad(foto: Foto) -> Path:
    pfad = (Path(settings.MEDIA_ROOT) / foto.dokument.speicher_schluessel).resolve()
    if Path(settings.MEDIA_ROOT).resolve() not in pfad.parents:
        raise FotoFehler("Ungültiger Speicherpfad.")
    return pfad
