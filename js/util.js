/* util.js — Persian text/number formatting helpers */
(function (G) {
  "use strict";

  var FA = "۰۱۲۳۴۵۶۷۸۹";

  function toFaDigits(s) {
    return String(s).replace(/[0-9]/g, function (d) { return FA[+d]; });
  }

  // group western digits with Persian thousands separator, then convert digits
  function group(n, dec) {
    var v = Number(n);
    if (!isFinite(v)) return "—";
    var s = v.toFixed(dec == null ? 0 : dec);
    var parts = s.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, "٬");
    return parts.join(".");
  }

  // fa(120.5, 0) -> "۱۲۰" ; fa(1234567) -> "۱٬۲۳۴٬۵۶۷"
  function fa(n, dec) {
    return toFaDigits(group(n, dec));
  }

  // faSigned with + prefix
  function faSigned(n, dec) {
    var v = Number(n);
    var s = fa(Math.abs(v), dec);
    return v >= 0 ? "+" + s : "−" + s;
  }

  // percent fa(9.9,1)+"٪"
  function faPct(n, dec) {
    return fa(n, dec == null ? 1 : dec) + "٪";
  }

  // compact number in toman -> "۲٫۲ میلیون"
  function faCompact(v, unit) {
    var abs = Math.abs(v);
    var parts = [];
    if (abs >= 1e9) parts = [v / 1e9, "میلیارد"];
    else if (abs >= 1e6) parts = [v / 1e6, "میلیون"];
    else if (abs >= 1e3) parts = [v / 1e3, "هزار"];
    else parts = [v, ""];
    var num = fa(parts[0], parts[0] >= 100 ? 0 : 1);
    return num + " " + parts[1] + (unit ? " " + unit : "");
  }

  // convert western number string in data keys to int year
  function numKeys(obj) {
    var out = {};
    Object.keys(obj).forEach(function (k) { out[+k] = obj[k]; });
    return out;
  }

  // tiny DOM helpers
  function h(tag, attrs, html) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (html != null) e.innerHTML = html;
    return e;
  }

  function svgEl(tag, attrs) {
    var e = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }

  function pct2(v) {
    // for range input fill gradient
    return v;
  }

  // Persian labels for known names
  var FA_NAME = {
    "Tehran": "تهران",
    "Karaj": "کرج",
    "Pardis": "پردیس",
    "Pakdasht": "پاکدشت",
    "Pishva": "پیشوا",
    "Robat Karim": "رباط‌کریم",
    "Shahriar": "شهریار",
    "Rey": "ری",
    "Eslamshahr": "اسلام‌شهر",
    "Varamin": "ورامین",
    "Hashtgerd": "هشتگرد",
    "Parand": "پرند"
  };

  G.util = {
    toFaDigits: toFaDigits,
    fa: fa,
    group: group,
    faSigned: faSigned,
    faPct: faPct,
    faCompact: faCompact,
    numKeys: numKeys,
    h: h,
    svgEl: svgEl,
    faName: function (n) { return FA_NAME[n] || n; }
  };
})(window.GH = window.GH || {});
