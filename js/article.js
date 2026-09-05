/* article.js — boot and initialization for the long-form article */
(function (G) {
  "use strict";

  var V = G.views;

  function setTheme(theme, persist) {
    document.documentElement.setAttribute("data-theme", theme);
    var ico = document.getElementById("theme-ico");
    var lbl = document.getElementById("theme-lbl");
    if (theme === "light") {
      if (ico) ico.textContent = "☀";
      if (lbl) lbl.textContent = "تم تیره";
    } else {
      if (ico) ico.textContent = "☾";
      if (lbl) lbl.textContent = "تم روشن";
    }
    if (persist) {
      try { localStorage.setItem("gh-theme", theme); } catch (e) {}
    }
    // Figures read palette colours from CSS variables, so redraw them in place.
    if (V && V.retheme) V.retheme();
  }

  function initThemeToggle() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var current = (document.documentElement.getAttribute("data-theme") || "dark") === "light" ? "light" : "dark";
    setTheme(current, false); // sync icon/label with what the head script applied
    btn.addEventListener("click", function () {
      var now = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      setTheme(now, true);
    });
  }

  function boot() {
    V.drawGas();
    V.drawPeriMap();
    V.drawParandRoute();
    V.drawRentWageIndex();
    V.drawNationalCommuteScale();
    V.buildMap();
    V.buildCalc();
    V.buildShock();
    V.initReveal();
    V.renderHeroStats();
    V.renderSources();
    initThemeToggle();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window.GH = window.GH || {});
