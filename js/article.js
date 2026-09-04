/* article.js — boot and initialization for the long-form article */
(function (G) {
  "use strict";

  var V = G.views;

  function boot() {
    V.drawGas();
    V.drawPeriMap();
    V.drawParandRoute();
    V.drawRentWageIndex();
    V.drawNational();
    V.buildMap();
    V.buildCalc();
    V.buildShock();
    V.initReveal();
    V.renderHeroStats();
    V.renderSources();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window.GH = window.GH || {});
