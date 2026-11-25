"""Make → Portal: eingehender Webhook für Anfragen (z. B. Webseiten-Formular oder WhatsApp über Make).

``POST /api/make/anfrage`` mit Header ``X-HH-Token: <MAKE_WEBHOOK_TOKEN>`` und JSON:
``{"name": "...", "email": "...", "telefon": "...", "plz": "33330", "ort": "...", "nachricht": "...",
"leistungen": ["Winterdienst"], "kanal": "webseite", "referenz": "<eindeutige ID aus Make>"}``

* Ohne gesetzten Token ist der Webhook aus (404). Vergleich in konstanter Zeit.
* ``referenz`` macht den Aufruf wiederholbar (Make wiederholt bei Fehlern) – kein Doppelanlegen.
* Legt Interessent (Kunde) + Anfrage an; das Ereignis ``anfrage.neu`` startet den Kundenservice-Agenten.
"""

import hmac
import json

from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from auftraege.models import Anfrage
from stammdaten.models import Kunde

from .http import env, protokollieren
from .models import SyncProtokoll

MAX_BYTES = 20_000
KANAELE = {"webseite", "whatsapp", "telefon", "email", "brief"}


@csrf_exempt
@require_POST
def anfrage(request):
    token = env("MAKE_WEBHOOK_TOKEN")
    if not token:
        raise Http404()
    if not hmac.compare_digest(request.headers.get("X-HH-Token", ""), token):
        protokollieren("make", "import", "anfrage", erfolgreich=False, http_status=401, fehler="Token ungültig")
        return JsonResponse({"fehler": "nicht berechtigt"}, status=401)
    if len(request.body) > MAX_BYTES:
        return JsonResponse({"fehler": "zu groß"}, status=413)
    try:
        d = json.loads(request.body)
        name = str(d["name"]).strip()[:200]
        assert name
    except (ValueError, KeyError, TypeError, AssertionError):
        return JsonResponse({"fehler": "JSON mit mindestens 'name' erwartet"}, status=400)
    referenz = str(d.get("referenz") or "")[:150]
    schluessel = f"make:anfrage:{referenz}" if referenz else None
    if schluessel:
        alt = SyncProtokoll.objects.filter(idempotenz_schluessel=schluessel).first()
        if alt:
            return JsonResponse({"anfrage_id": str(alt.lokale_id), "doppelt": True})
    plz = str(d.get("plz") or "").strip()
    plz = plz if len(plz) == 5 and plz.isdigit() else None
    email = (str(d.get("email") or "").strip().lower() or None)
    with transaction.atomic():
        kunde = (Kunde.objects.filter(email__iexact=email).first() if email else None)
        if kunde is None:
            try:
                with transaction.atomic():
                    kunde = Kunde.objects.create(name=name, typ="privat", status="interessent", email=email,
                                                 telefon=str(d.get("telefon") or "")[:50] or None, plz=plz,
                                                 ort=str(d.get("ort") or "")[:100] or None, quelle="Make-Webhook")
            except IntegrityError:
                kunde = Kunde.objects.filter(name__iexact=name, plz=plz).first()
        leistungen = [str(x)[:60] for x in (d.get("leistungen") or [])][:10] or None
        a = Anfrage.objects.create(kunde=kunde, kanal=d.get("kanal") if d.get("kanal") in KANAELE else "webseite",
                                   betreff=f"Anfrage von {name}"[:300], gewuenschte_leistungen=leistungen,
                                   ki_zusammenfassung=str(d.get("nachricht") or "")[:4000] or None)
        protokollieren("make", "import", "anfrage", lokale_id=a.id, externe_id=referenz or None, schluessel=schluessel,
                       erfolgreich=True, http_status=201)
    return JsonResponse({"anfrage_id": str(a.id), "anfragenummer": a.anfragenummer}, status=201)
