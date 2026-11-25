// Hausmeister Helden – kleine Helfer, ohne Tracking, ohne externe Skripte.
(function () {
  var WA = "4952413389748";
  var MAIL = "info@haus-meister-helden.de";

  // Menü
  var t = document.querySelector(".nav-toggle"), n = document.getElementById("nav");
  if (t && n) {
    t.addEventListener("click", function () {
      var o = n.classList.toggle("open");
      t.setAttribute("aria-expanded", o ? "true" : "false");
    });
    n.addEventListener("click", function (e) { if (e.target.tagName === "A") { n.classList.remove("open"); t.setAttribute("aria-expanded", "false"); } });
  }

  // Einblenden beim Scrollen
  var els = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -8% 0px" });
    els.forEach(function (el) { io.observe(el); });
  } else { els.forEach(function (el) { el.classList.add("in"); }); }

  // Preisrechner – Preise kommen aus portal/app/vertrieb/preisliste.json (von build.py eingebettet, netto, Cent)
  var calc = document.getElementById("rechner"), PE = document.getElementById("hh-preise");
  if (calc && PE) {
    var PR = JSON.parse(PE.textContent), WD = PR.wd;
    var W = 52 / 12, $ = function (id) { return calc.querySelector("#" + id); };
    var num = function (id) { var v = parseFloat($(id).value); return isNaN(v) || v < 0 ? 0 : v; };
    var total = $("summe"), list = $("aufstellung"), cta = $("rechner-cta");
    var eur = function (v) { return v.toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + " €"; };
    function upd() {
      var on = {}; calc.querySelectorAll("input[name=l]").forEach(function (c) { on[c.value] = c.checked; });
      calc.querySelectorAll(".calc-grid .field").forEach(function (f) { f.hidden = !on[f.getAttribute("data-for")]; });
      var rows = [], sum = 0, text = [];
      if (on.reinigung) {
        var th = Math.max(1, num("r-th")), et = Math.max(1, num("r-et")), z = $("r-int").value === "z";
        var proR = th * (PR.th_grund + PR.th_etage * et) / 100 * (z ? 1 + PR.th_zuschlag : 1), v = proR * (z ? W / 2 : W);
        sum += v; rows.push(["Treppenhausreinigung (" + (z ? "14-täglich" : "wöchentlich") + ")", eur(v)]);
        text.push("Treppenhaus " + th + "x" + et + " Etagen " + (z ? "14-täglich" : "wöchentlich"));
      }
      if (on.garten) { var g = num("r-qm") * 0.35; sum += g; rows.push(["Gartenpflege (" + num("r-qm") + " m²)", eur(g)]); text.push("Garten " + num("r-qm") + " m²"); }
      if (on.muell) { var m = num("r-ab") * (PR.mu_termin + 2 * PR.mu_leerung) / 100; sum += m; rows.push(["Mülltonnen-Service", eur(m)]); text.push("Mülltonnen " + num("r-ab") + " Termine/Monat"); }
      var wtxt = "";
      if (on.winter) {
        var lfm = num("r-m"), mehr = Math.max(0, lfm - WD.grund_meter);
        var streu = (WD.streu_bis_25m + WD.streu_je_weiterer_m * mehr) / 100, raeum = (WD.raeum_bis_25m + WD.raeum_je_weiterer_m * mehr) / 100;
        var eur2 = function (v) { return v.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"; };
        rows.push(["Winterdienst: Bereitstellung je Saison", eur2(WD.bereitstellung / 100)]);
        rows.push(["… je Streueinsatz / Räumen + Streuen (" + lfm + " m)", eur2(streu) + " / " + eur2(raeum)]);
        rows.push(["… oder Saisonpauschale, alle Einsätze inkl.", eur2((PR.wd_grund + PR.wd_lfm * lfm) / 100)]);
        wtxt = " + Winterdienst (Bereitstellung " + eur2(WD.bereitstellung / 100) + "/Saison + " + eur2(streu) + " je Einsatz)";
        text.push("Winterdienst " + lfm + " m");
      }
      total.textContent = (sum || !on.winter) ? eur(sum) : "– €";
      list.innerHTML = rows.length ? rows.map(function (r) { return "<li><span>" + r[0] + "</span><b>" + r[1] + "</b></li>"; }).join("") + (sum ? "<li><span>inkl. 19 % MwSt.</span><b>" + eur(sum * 1.19) + "</b></li>" : "") : "<li><span>Bitte mindestens eine Leistung wählen</span></li>";
      var msg = "Hallo Hausmeister Helden, ich hätte gern ein Festpreis-Angebot: " + (text.join(", ") || "Hausmeisterservice") + ". Richtwert laut Rechner: ca. " + eur(sum) + " netto/Monat" + wtxt + ".";
      cta.href = "https://wa.me/" + WA + "?text=" + encodeURIComponent(msg);
    }
    calc.addEventListener("input", upd); calc.addEventListener("change", upd); upd();
  }

  // Anfrageformular: baut eine WhatsApp-Nachricht oder E-Mail – es werden keine Daten auf dem Server gespeichert.
  var f = document.getElementById("anfrage");
  if (f) {
    function text() {
      var d = new FormData(f), s = "Anfrage über die Webseite\n";
      [["name", "Name"], ["firma", "Firma/Verwaltung"], ["telefon", "Telefon"], ["ort", "Objekt/Ort"], ["leistung", "Leistung"], ["nachricht", "Nachricht"]].forEach(function (k) {
        var v = (d.get(k[0]) || "").toString().trim(); if (v) s += k[1] + ": " + v + "\n";
      });
      return s;
    }
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!f.reportValidity()) return;
      var via = e.submitter && e.submitter.value === "mail" ? "mail" : "wa";
      if (via === "mail") location.href = "mailto:" + MAIL + "?subject=" + encodeURIComponent("Anfrage Hausmeisterservice") + "&body=" + encodeURIComponent(text());
      else window.open("https://wa.me/" + WA + "?text=" + encodeURIComponent(text()), "_blank", "noopener");
    });
  }
})();
