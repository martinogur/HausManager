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

  // Preisrechner (Richtwerte von der Webseite, Preise in firma/profil.md)
  var calc = document.getElementById("rechner");
  if (calc) {
    var WEEKS = 52 / 12;
    var P = {
      reinigung: { label: "Treppenhausreinigung", per: function (u) { return u * 8 * WEEKS * 0.9; }, hint: "wöchentlich, inkl. 10 % Treuerabatt" },
      winter: { label: "Winterdienst", per: function (u) { return u * 8 * WEEKS; }, hint: "Okt–März" },
      garten: { label: "Gartenarbeit", per: function (u) { return u * 30; } },
      muell: { label: "Mülltonnen-Service", per: function (u) { return u * 5; } },
      reparatur: { label: "Kleinreparaturen", per: null, hint: "35 € / Std. nach Aufwand" }
    };
    var units = calc.querySelector("#einheiten"), out = calc.querySelector("#einheiten-out");
    var total = calc.querySelector("#summe"), list = calc.querySelector("#aufstellung"), cta = calc.querySelector("#rechner-cta");
    var eur = function (v) { return Math.round(v).toLocaleString("de-DE") + " €"; };
    function upd() {
      var u = +units.value; out.value = u;
      var sum = 0, rows = [], chosen = [];
      calc.querySelectorAll("input[name=l]:checked").forEach(function (c) {
        var p = P[c.value]; chosen.push(p.label);
        if (p.per) { var v = p.per(u); sum += v; rows.push("<li><span>" + p.label + (p.hint ? " <small>(" + p.hint + ")</small>" : "") + "</span><b>" + eur(v) + "</b></li>"); }
        else rows.push("<li><span>" + p.label + "</span><b>" + p.hint + "</b></li>");
      });
      total.textContent = rows.length ? eur(sum) : "– €";
      list.innerHTML = rows.length ? rows.join("") : "<li><span>Bitte mindestens eine Leistung wählen</span></li>";
      var msg = "Hallo Hausmeister Helden, ich interessiere mich für: " + (chosen.join(", ") || "Hausmeisterservice") + " für ca. " + u + " Wohneinheiten. Der Rechner zeigt ca. " + eur(sum) + " / Monat. Bitte um ein konkretes Angebot.";
      cta.href = "https://wa.me/" + WA + "?text=" + encodeURIComponent(msg);
    }
    calc.addEventListener("input", upd); upd();
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
