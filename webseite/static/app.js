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

  // Preisrechner – Preise laut akquise/angebote/preiskalkulation.md (netto)
  var calc = document.getElementById("rechner");
  if (calc) {
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
        var proR = th * (12 + 8 * et) * (z ? 1.15 : 1), v = proR * (z ? W / 2 : W);
        sum += v; rows.push(["Treppenhausreinigung (" + (z ? "14-täglich" : "wöchentlich") + ")", eur(v)]);
        text.push("Treppenhaus " + th + "x" + et + " Etagen " + (z ? "14-täglich" : "wöchentlich"));
      }
      if (on.garten) { var g = num("r-qm") * 0.35; sum += g; rows.push(["Gartenpflege (" + num("r-qm") + " m²)", eur(g)]); text.push("Garten " + num("r-qm") + " m²"); }
      if (on.muell) { var m = num("r-ab") * (6.5 + 2 * 1.34); sum += m; rows.push(["Mülltonnen-Service", eur(m)]); text.push("Mülltonnen " + num("r-ab") + " Termine/Monat"); }
      var wtxt = "";
      if (on.winter) { var ws = 220 + 9.5 * num("r-m"); rows.push(["Winterdienst je Saison (" + num("r-m") + " m)", eur(ws)]); wtxt = " + Winterdienst " + eur(ws) + "/Saison"; text.push("Winterdienst " + num("r-m") + " m"); }
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
