/* views.js — scene renderers for the long-form article */
(function (G) {
  "use strict";

  var D = window.ARTICLE_DATA;
  var u = G.util;

  function el(id) { return document.getElementById(id); }

  /* ---------- color helpers ---------- */
  function hex2rgb(h) {
    var n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function mix(a, b, t) {
    var A = hex2rgb(a), B = hex2rgb(b);
    var c = A.map(function (x, i) { return Math.round(x + (B[i] - x) * t); });
    return "rgb(" + c.join(",") + ")";
  }

  /* ============================================================
     FIGURE 1 — gasoline daily consumption line chart (1382–1402)
     ============================================================ */
  var GAS_SVG = null;

  function drawGas() {
    var data = u.numKeys(D.annual.gasoline);
    var years = Object.keys(data).map(Number).sort(function (a, b) { return a - b; });
    var y0 = years[0], y1 = years[years.length - 1];
    var vmax = 140;

    var W = 720, H = 400, pl = 42, pr = 26, pt = 30, pb = 46;
    var iw = W - pl - pr, ih = H - pt - pb;
    var X = function (y) { return pl + (y - y0) / (y1 - y0) * iw; };
    var Y = function (v) { return pt + (1 - v / vmax) * ih; };

    var pts = years.map(function (y) { return [X(y), Y(data[y]), y, data[y]]; });

    var linePath = pts.map(function (p, i) {
      return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1);
    }).join(" ");
    var areaPath = linePath + " L" + X(y1).toFixed(1) + " " + (pt + ih) +
      " L" + X(y0).toFixed(1) + " " + (pt + ih) + " Z";

    if (!GAS_SVG) {
      GAS_SVG = u.svgEl("svg", { viewBox: "0 0 " + W + " " + H, "class": "g-chart", role: "img", "aria-label": "نمودار مصرف روزانه بنزین ایران از ۱۳۸۲ تا ۱۴۰۴" });
      el("gas-chart").appendChild(GAS_SVG);
    }
    GAS_SVG.innerHTML = "";

    var defs = u.svgEl("defs");
    defs.innerHTML = '<linearGradient id="ggrad" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#f2b632" stop-opacity="0.32"/>' +
      '<stop offset="1" stop-color="#f2b632" stop-opacity="0.02"/></linearGradient>';
    GAS_SVG.appendChild(defs);

    [40, 80, 120].forEach(function (v) {
      var y = Y(v);
      GAS_SVG.appendChild(u.svgEl("line", { x1: pl, x2: W - pr, y1: y, y2: y, "class": "grid-line" }));
      var t = u.svgEl("text", { x: pl - 8, y: y + 4, "class": "axis-txt", "text-anchor": "end" });
      t.textContent = u.toFaDigits(v);
      GAS_SVG.appendChild(t);
    });
    [1382, 1386, 1390, 1394, 1398, 1402, 1404].forEach(function (y) {
      var t = u.svgEl("text", { x: X(y), y: H - 12, "class": "axis-txt", "text-anchor": "middle" });
      t.textContent = u.toFaDigits(y);
      GAS_SVG.appendChild(t);
    });

    GAS_SVG.appendChild(u.svgEl("path", { d: areaPath, fill: "url(#ggrad)" }));
    GAS_SVG.appendChild(u.svgEl("path", { d: linePath, fill: "none", stroke: "#f2b632", "stroke-width": 3, "stroke-linejoin": "round", "stroke-linecap": "round" }));

    // 1399 covid dip marker
    var cy = 1399;
    GAS_SVG.appendChild(u.svgEl("line", { x1: X(cy), x2: X(cy), y1: Y(data[cy]) + 14, y2: Y(120), stroke: "#7fb7ff", "stroke-dasharray": "3 5", "stroke-width": 1, opacity: 0.7 }));

    // point dots with hover tooltips
    pts.forEach(function (p) {
      var c = u.svgEl("circle", { cx: p[0], cy: p[1], r: p[3] >= 100 ? 6 : 4, fill: p[3] >= 100 ? "#f2b632" : "#0c0f15", stroke: "#f2b632", "stroke-width": p[3] >= 100 ? 3 : 2, style: "cursor:pointer" });
      var t = u.svgEl("title");
      t.textContent = "سال " + u.toFaDigits(p[2]) + " — " + u.toFaDigits(p[3]) + " میلیون لیتر در روز";
      c.appendChild(t);
      GAS_SVG.appendChild(c);
    });

    // endpoint labels
    function endLabel(y, label, dy) {
      var t = u.svgEl("text", { x: X(y), y: Y(data[y]) + (dy || -14), "text-anchor": X(y) < W / 2 ? "start" : "end", "class": "axis-txt", "font-size": "13", fill: "#f2b632", "font-weight": "800" });
      t.textContent = label;
      GAS_SVG.appendChild(t);
    }
    endLabel(y0, u.toFaDigits(data[y0]) + " · " + u.toFaDigits(y0));
    endLabel(y1, u.toFaDigits(data[y1]) + " · " + u.toFaDigits(y1));
    // covid label
    var tl = u.svgEl("text", { x: X(cy) + 8, y: Y(data[cy]) - 10, "class": "axis-txt", "font-size": "11", fill: "#7fb7ff" });
    tl.textContent = "۱۳۹۹ · کرونا";
    GAS_SVG.appendChild(tl);

    el("gas-legend").innerHTML =
      '<span>منبع: گزارش‌های وزارت نفت/شانا (مشاهده‌شده)</span>' +
      '<span>افت ۱۳۹۹ ← محدودیت‌های کرونایی</span>';
  }

  /* ============================================================
     FIGURE 3 — Tehran metropolitan-region built-up growth map
     (schematic proportional-symbol map)
     ============================================================ */
  var PERI = {
    // county -> [x, y] approx projected on the schematic canvas
    pos: {
      "Tehran": [535, 202],
      "Pardis": [894, 150],
      "Pakdasht": [805, 372],
      "Pishva": [856, 512],
      "Robat Karim": [257, 366],
      "Shahriar": [230, 230],
      "Rey": [577, 282],
      "Parand": [128, 386]
    },
    selected: null
  };
  var PERI_RMAX = 58;

  function periData(name) {
    var p = D.periphery[name];
    return p ? p.built_up_growth_2010_2020 : null;
  }

  function drawPeriMap() {
    var names = ["Pardis", "Pishva", "Pakdasht", "Robat Karim", "Shahriar", "Rey", "Tehran"];
    var values = {};
    var maxG = 1;
    names.forEach(function (n) { var d = periData(n); if (d) { values[n] = d.value; maxG = Math.max(maxG, d.value); } });

    var W = 1000, H = 600;
    var svg = u.svgEl("svg", { viewBox: "0 0 " + W + " " + H, id: "peri-svg", role: "img", "aria-label": "نقشه رشد سطح ساخته‌شده منطقه کلان‌شهری تهران" });

    // subtle guide: faint metro halo around Tehran
    var halo = u.svgEl("circle", { cx: PERI.pos.Tehran[0], cy: PERI.pos.Tehran[1], r: 150, fill: "rgba(242,182,50,0.05)", stroke: "rgba(242,182,50,0.18)", "stroke-dasharray": "4 6", "stroke-width": 1 });
    svg.appendChild(halo);

    // dashed links to Tehran
    names.forEach(function (n) {
      if (n === "Tehran") return;
      var p = PERI.pos[n];
      svg.appendChild(u.svgEl("line", { x1: p[0], y1: p[1], x2: PERI.pos.Tehran[0], y2: PERI.pos.Tehran[1], stroke: "rgba(255,255,255,0.14)", "stroke-dasharray": "3 6", "stroke-width": 1 }));
    });

    function label(n, x, y, txt, fill, anchor) {
      var t = u.svgEl("text", { x: x, y: y, "text-anchor": anchor || "middle", "class": "axis-txt", "font-size": "13", fill: fill || "#a4aeba", "font-weight": "600" });
      t.textContent = txt;
      svg.appendChild(t);
    }

    // Tehran centre marker
    var tc = PERI.pos.Tehran;
    label("Tehran", tc[0], tc[1] - 16, "تهران (مرکز اشتغال)", "#f2b632", "middle");

    names.forEach(function (n) {
      if (n === "Tehran") return;
      var p = PERI.pos[n];
      var v = values[n];
      if (v == null) return;
      var r = Math.max(7, Math.sqrt(v / maxG) * PERI_RMAX);
      var color = mix("#3b4353", "#f2b632", Math.pow(v / maxG, 0.6));
      var c = u.svgEl("circle", { cx: p[0], cy: p[1], r: r, fill: color, "class": "county", "data-name": n, opacity: 0.92 });
      var t = u.svgEl("title");
      t.textContent = u.faName(n) + " — " + u.toFaDigits(v, 1) + "٪ رشد";
      c.appendChild(t);
      svg.appendChild(c);
      label(n, p[0], p[1] + r + 15, u.faName(n), "#edf0f5", "middle");
      label("v-" + n, p[0], p[1] - r - 6, u.toFaDigits(u.group(v, 1)) + "٪", "#f2b632", "middle");
    });

    // north arrow + scale note (decorative, honest about schematic nature)
    var comp = u.svgEl("text", { x: 20, y: 30, "class": "axis-txt", "font-size": "11", fill: "#6c7788" });
    comp.textContent = "شماتیک — موقعیت‌ها تقریبی‌اند؛ اندازه دایره = رشد ۲۰۱۰–۲۰۲۰";
    svg.appendChild(comp);

    var host = el("peri-map");
    host.innerHTML = "";
    host.appendChild(svg);

    // interactions
    svg.addEventListener("click", function (e) {
      var c = e.target.closest ? e.target.closest(".county") : null;
      if (!c) return;
      PERI.selected = c.getAttribute("data-name");
      paintPeri(svg, values);
      updatePeriDetail(values);
    });
    paintPeri(svg, values);
    updatePeriDetail(values);
    el("peri-note").textContent =
      "میزان رشد: پردیس ۲۴۴.۸٪ · پیشوا ۱۸۷.۸٪ · پاکدشت ۱۶۲.۳٪ · رباط‌کریم ۱۳۸.۵٪ · شهریار ۸۲.۹٪ · ری ۵۸٪ · تهران ۴.۸٪ (منبع: پژوهش منطقه کلان‌شهری تهران — مشاهده‌شده).";
  }

  function paintPeri(svg, values) {
    var cs = svg.querySelectorAll(".county");
    for (var i = 0; i < cs.length; i++) {
      cs[i].classList.toggle("sel", cs[i].getAttribute("data-name") === PERI.selected);
    }
  }

  function updatePeriDetail(values) {
    var box = el("peri-detail");
    if (!PERI.selected) {
      box.innerHTML = "روی هر شهرستان بزن تا میزان رشد را ببینی. سبز/کهربایی پررنگ‌تر یعنی رشد سریع‌تر.";
      return;
    }
    var n = PERI.selected;
    var v = values[n];
    var isTeh = n === "Tehran";
    box.innerHTML = isTeh
      ? "<b>تهران (شهرستان)</b> — مرکز اشتغال؛ رشد سطح ساخته‌شده ۲۰۱۰–۲۰۲۰ فقط <b>~۵٪</b>."
      : "<b>" + u.faName(n) + "</b> — رشد سطح ساخته‌شده ۲۰۱۰–۲۰۲۰ حدود <b>" + u.toFaDigits(u.group(v, 1)) + "٪</b>؛ چند برابر تهران.";
  }

  /* ============================================================
     FIGURE 4 — Parand route stepper (one-way / daily / monthly)
     ============================================================ */
  var PARAND = { stage: "day" };

  function drawParandRoute() {
    var W = 1000, H = 300;
    var svg = u.svgEl("svg", { viewBox: "0 0 " + W + " " + H, id: "parand-svg", role: "img", "aria-label": "شماتیک مسیر پرند تا تهران" });

    var parX = 190, tehX = 830, y = 150;
    var par = { x: parX, y: y, name: "پرند" };
    var teh = { x: tehX, y: y, name: "تهران" };

    // city blocks
    function city(cx, cy, name, w) {
      var r = u.svgEl("rect", { x: cx - w / 2, y: cy - 46, width: w, height: 92, rx: 14, fill: "#1b2230", stroke: "rgba(242,182,50,0.4)", "stroke-width": 1.5 });
      svg.appendChild(r);
      var t = u.svgEl("text", { x: cx, y: cy + 6, "text-anchor": "middle", "class": "axis-txt", "font-size": "20", fill: "#edf0f5", "font-weight": "800" });
      t.textContent = name;
      svg.appendChild(t);
    }
    city(parX, y, "پرند", 220);
    city(tehX, y, "تهران", 240);

    // road
    svg.appendChild(u.svgEl("line", { x1: parX + 110, y1: y, x2: tehX - 120, y2: y, stroke: "#39414f", "stroke-width": 4 }));
    svg.appendChild(u.svgEl("line", { x1: parX + 110, y1: y, x2: tehX - 120, y2: y, stroke: "#f2b632", "stroke-width": 2, "stroke-dasharray": "10 8", opacity: 0.85 }));

    // moving pulse marker
    var marker = u.svgEl("circle", { cx: parX + 110, cy: y, r: 9, fill: "#f2b632" });
    var anim = u.svgEl("animateMotion", { dur: "3.2s", repeatCount: "indefinite", path: "M " + (parX + 110) + " " + y + " L " + (tehX - 120) + " " + y });
    marker.appendChild(anim);
    svg.appendChild(marker);

    // distance bracket (one-way 35–50 km) drawn under the road
    var by = y + 70;
    var seg = u.svgEl("g", { "class": "seg" });
    seg.appendChild(u.svgEl("line", { x1: parX + 110, y1: by, x2: tehX - 120, y2: by, stroke: "#7fb7ff", "stroke-width": 1.4 }));
    seg.appendChild(u.svgEl("line", { x1: parX + 110, y1: by - 8, x2: parX + 110, y2: by + 8, stroke: "#7fb7ff", "stroke-width": 1.4 }));
    seg.appendChild(u.svgEl("line", { x1: tehX - 120, y1: by - 8, x2: tehX - 120, y2: by + 8, stroke: "#7fb7ff", "stroke-width": 1.4 }));
    var lab = u.svgEl("text", { x: (parX + tehX) / 2, y: by + 30, "text-anchor": "middle", "class": "axis-txt", "font-size": "16", fill: "#7fb7ff", "font-weight": "800" });
    lab.textContent = "یک‌طرفه: ۳۵ تا ۵۰ کیلومتر";
    seg.appendChild(lab);
    svg.appendChild(seg);

    var host = el("parand-route");
    host.innerHTML = "";
    host.appendChild(svg);

    // stage chips + stat cards
    var stages = [
      { id: "oneway", label: "۱ · فاصله یک‌طرفه", stat: { v: "۳۵–۵۰", l: "کیلومتر یک‌طرفه (مقصد داخل تهران)" } },
      { id: "day", label: "۲ · رفت‌وبرگشت روزانه", stat: { v: "~۱۰۰", l: "کیلومتر در روز، برای بعضی مسیرها" } },
      { id: "month", label: "۳ · مسافت ماهانه", stat: { v: "۲٬۲۰۰", l: "کیلومتر در ماه (۲۲ روز کاری)" } }
    ];
    var stats = el("parand-stats");
    stats.innerHTML = "";
    var chipsWrap = u.h("div", { "class": "chips", style: "margin-top:.9rem" });
    stages.forEach(function (s) {
      var b = u.h("button", { type: "button", "class": "chip" + (s.id === PARAND.stage ? " active" : ""), "data-stage": s.id }, s.label);
      b.addEventListener("click", function () {
        PARAND.stage = s.id;
        var cs = chipsWrap.children;
        for (var i = 0; i < cs.length; i++) cs[i].classList.toggle("active", cs[i].getAttribute("data-stage") === s.id);
        renderParandStats();
      });
      chipsWrap.appendChild(b);
    });
    stats.appendChild(chipsWrap);
    renderParandStats();
  }

  function renderParandStats() {
    var defs = {
      oneway: { v: "۳۵–۵۰", l: "کیلومتر یک‌طرفه، وقتی مقصد داخل تهران است (برآورد)" },
      day: { v: "~۱۰۰", l: "کیلومتر رفت‌وبرگشت روزانه؛ ۳۰ تا ۴۰ هزار مسافر در روز (برآورد)" },
      month: { v: "۲٬۲۰۰", l: "کیلومتر در ماه برای رفتن به سر کار، با ۲۲ روز کاری (محاسبه)" }
    };
    var d = defs[PARAND.stage];
    var stats = el("parand-stats");
    var existing = stats.querySelector(".parand-stat");
    if (existing) existing.remove();
    var card = u.h("div", { "class": "parand-stat" }, '<div class="v">' + d.v + "</div><div class='l'>" + d.l + "</div>");
    // insert after chips
    stats.appendChild(card);
  }

  /* ============================================================
     FIGURE 2b — Tehran rent index vs minimum-wage index (1388=100)
     ============================================================ */
  function citywideRent() {
    var agg = {}, cnt = {};
    var dd = D.district_annual_rent;
    Object.keys(dd).forEach(function (r) {
      var yd = dd[r];
      Object.keys(yd).forEach(function (y) {
        agg[y] = (agg[y] || 0) + yd[y];
        cnt[y] = (cnt[y] || 0) + 1;
      });
    });
    var out = {};
    Object.keys(agg).forEach(function (y) { out[+y] = agg[y] / cnt[y]; });
    return out;
  }

  function drawRentWageIndex() {
    var rent = citywideRent();
    var mw = u.numKeys(D.annual.min_wage);
    var baseR = rent[1388], baseW = mw[1388] / 10;
    var years = Object.keys(rent).map(Number).sort(function (a, b) { return a - b; });
    var idxR = {}, idxW = {};
    var ymax = 100;
    years.forEach(function (y) {
      idxR[y] = rent[y] / baseR * 100;
      idxW[y] = (mw[y] / 10) / baseW * 100;
      ymax = Math.max(ymax, idxR[y], idxW[y]);
    });
    ymax = Math.ceil((ymax + 20) / 200) * 200;

    var W = 720, H = 300, pl = 46, pr = 26, pt = 26, pb = 42;
    var iw = W - pl - pr, ih = H - pt - pb;
    var X = function (y) { return pl + (y - 1388) / (1400 - 1388) * iw; };
    var Y = function (v) { return pt + (1 - v / ymax) * ih; };

    var host = el("rent-wage-chart");
    var svg = u.svgEl("svg", { viewBox: "0 0 " + W + " " + H, "class": "g-chart", role: "img", "aria-label": "شاخص اجاره تهران و حداقل دستمزد از ۱۳۸۸" });
    host.innerHTML = "";
    host.appendChild(svg);

    [200, 400, 600, 800, 1000].forEach(function (v) {
      if (v > ymax) return;
      var y = Y(v);
      svg.appendChild(u.svgEl("line", { x1: pl, x2: W - pr, y1: y, y2: y, "class": "grid-line" }));
      var t = u.svgEl("text", { x: pl - 8, y: y + 4, "class": "axis-txt", "text-anchor": "end" });
      t.textContent = u.toFaDigits(v);
      svg.appendChild(t);
    });
    [1388, 1392, 1396, 1400].forEach(function (y) {
      var t = u.svgEl("text", { x: X(y), y: H - 10, "class": "axis-txt", "text-anchor": "middle" });
      t.textContent = u.toFaDigits(y);
      svg.appendChild(t);
    });

    function linePath(map) {
      return years.map(function (y, i) {
        return (i ? "L" : "M") + X(y).toFixed(1) + " " + Y(map[y]).toFixed(1);
      }).join(" ");
    }
    svg.appendChild(u.svgEl("path", { d: linePath(idxR), fill: "none", stroke: "#f2b632", "stroke-width": 3, "stroke-linejoin": "round" }));
    svg.appendChild(u.svgEl("path", { d: linePath(idxW), fill: "none", stroke: "#7fb7ff", "stroke-width": 2.4, "stroke-linejoin": "round", "stroke-dasharray": "1 0" }));

    // end labels (anchor to the right so they stay inside the viewBox)
    function endLbl(map, txt, fill, dy) {
      var t = u.svgEl("text", { x: X(1400) - 8, y: Y(map[1400]) + (dy || -8), "text-anchor": "end", "class": "axis-txt", "font-size": "12", fill: fill, "font-weight": "800" });
      t.textContent = txt;
      svg.appendChild(t);
    }
    endLbl(idxR, "اجاره ≈ " + u.toFaDigits(Math.round(idxR[1400])), "#f2b632", -10);
    endLbl(idxW, "حداقل دستمزد ≈ " + u.toFaDigits(Math.round(idxW[1400])), "#7fb7ff", 18);

    // inline legend (top-left)
    var t1 = u.svgEl("text", { x: pl, y: 18, "class": "axis-txt", "font-size": "12", fill: "#f2b632", "font-weight": "700" });
    t1.textContent = "— اجاره (میانگین ۲۲ منطقه)";
    svg.appendChild(t1);
    var t2 = u.svgEl("text", { x: pl + 200, y: 18, "class": "axis-txt", "font-size": "12", fill: "#7fb7ff", "font-weight": "700" });
    t2.textContent = "— حداقل دستمزد قانونی";
    svg.appendChild(t2);
  }

  /* ============================================================
     FIGURE 2 — Tehran 22-district affordability map
     ============================================================ */
  var MAP = { year: 1388, mult: 2, size: 35, share: 35, selected: null };

  var AFF_STOPS = [[0, "#1e9e63"], [0.55, "#3ec47f"], [1, "#9ce6ac"]];
  function affColor(ratio) {
    if (ratio == null) return null;
    var t = Math.min(ratio, 1);
    var i = 0;
    while (i < AFF_STOPS.length - 2 && t > AFF_STOPS[i + 1][0]) i++;
    var a = AFF_STOPS[i], b = AFF_STOPS[i + 1];
    var tt = b[0] === a[0] ? 0 : (t - a[0]) / (b[0] - a[0]);
    return mix(a[1], b[1], tt);
  }

  function districtRent(regStr, year) {
    var yd = D.district_annual_rent[regStr];
    return yd ? yd[String(year)] : undefined;
  }

  function mapBudget() {
    return D.annual.min_wage[String(MAP.year)] / 10 * MAP.mult * (MAP.share / 100);
  }

  function ratioFor(regStr) {
    var rent = districtRent(regStr, MAP.year);
    if (rent == null) return null;
    return (rent * MAP.size) / mapBudget();
  }

  function regionName(regStr) {
    return D.district_names[regStr] || ("منطقه " + u.toFaDigits(regStr));
  }

  function mapSummary() {
    var n = 0;
    Object.keys(D.district_names).forEach(function (r) {
      var rt = ratioFor(r);
      if (rt != null && rt <= 1) n++;
    });
    return n;
  }

  function buildMap() {
    var geo = window.TEHRAN_GEO;
    var svg = el("map-svg");
    svg.setAttribute("viewBox", "0 0 1000 " + geo.height);
    svg.innerHTML = "";

    var defs = u.svgEl("defs");
    defs.innerHTML = '<pattern id="hatch" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">' +
      '<rect width="6" height="6" fill="#262c37"/><line x1="0" y1="0" x2="0" y2="6" stroke="#3a4250" stroke-width="2"/></pattern>';
    svg.appendChild(defs);

    geo.districts.forEach(function (d) {
      var regStr = String(d.region);
      var dpath = d.rings.map(function (ring) {
        return "M" + ring.map(function (p) { return p[0] + " " + p[1]; }).join("L") + "Z";
      }).join(" ");
      var path = u.svgEl("path", { d: dpath, "class": "district", "data-reg": regStr });
      var title = u.svgEl("title");
      title.textContent = regionName(regStr);
      path.appendChild(title);
      svg.appendChild(path);
    });

    el("map-legend").innerHTML =
      '<span><span class="sw" style="background:#3ec47f"></span>داخل توان اجاره</span>' +
      '<span><span class="sw" style="background:#39414f"></span>خارج از توان</span>' +
      '<span><span class="sw" style="background:repeating-linear-gradient(45deg,#262c37,#262c37 3px,#3a4250 3px,#3a4250 6px)"></span>فاقد داده</span>';

    var chips = el("map-income");
    chips.innerHTML = "";
    [1, 2, 3, 5].forEach(function (m) {
      var b = u.h("button", { type: "button", "class": "chip" + (m === MAP.mult ? " active" : ""), "data-mult": m }, "×" + u.toFaDigits(m) + " حداقل دستمزد");
      b.addEventListener("click", function () {
        MAP.mult = m;
        syncMapControls();
        updateMap();
      });
      chips.appendChild(b);
    });

    svg.addEventListener("click", function (e) {
      var p = e.target.closest ? e.target.closest(".district") : null;
      if (p) { MAP.selected = p.getAttribute("data-reg"); paintMap(); updateDetail(); }
    });
    svg.addEventListener("pointerover", function (e) {
      var p = e.target.closest ? e.target.closest(".district") : null;
      if (p) paintOne(p, false);
    });
    svg.addEventListener("pointerout", function () { paintMap(); });

    function bindSlider(id, key, min, max, set) {
      var inp = el(id);
      inp.addEventListener("input", function () {
        MAP[key] = +inp.value;
        syncMapControls();
        updateMap();
      });
    }
    bindSlider("map-year", "year");
    bindSlider("map-size", "size");
    bindSlider("map-share", "share");

    syncMapControls();
    updateMap();
  }

  function syncMapControls() {
    el("map-year").value = MAP.year;
    el("map-size").value = MAP.size;
    el("map-share").value = MAP.share;
    el("map-year-lbl").textContent = u.toFaDigits(MAP.year);
    el("map-size-lbl").textContent = u.toFaDigits(MAP.size) + " متر";
    el("map-share-lbl").textContent = u.toFaDigits(MAP.share) + "٪";
    var chips = el("map-income").children;
    for (var i = 0; i < chips.length; i++) {
      chips[i].classList.toggle("active", +chips[i].getAttribute("data-mult") === MAP.mult);
    }
    updateMapNote();
  }

  function affordableRegions() {
    var ids = [];
    Object.keys(D.district_names).forEach(function (r) {
      var rt = ratioFor(r);
      if (rt != null && rt <= 1) ids.push(+r);
    });
    return ids;
  }

  function updateMapNote() {
    var ids = affordableRegions();
    var n = ids.length;
    var mwT = u.faCompact(D.annual.min_wage[String(MAP.year)] / 10 * MAP.mult, "تومان");
    var extra = "";
    if (MAP.mult === 1 && n === 0) {
      extra = " با حداقل دستمزد، طبق همین فرض‌های مدل (متراژ و سقف سهم اجاره)، هیچ منطقه‌ای از آستانه نمی‌گذرد. این فقط نتیجه این مدل است، نه پیش‌بینی محل سکونت خانوارها.";
    } else if (n > 0 && n < 7) {
      // conservative geography clause only for small affordable sets
      var se = [15, 16, 17, 18, 19, 20];
      var allSE = ids.every(function (id) { return se.indexOf(id) !== -1; });
      if (allSE) {
        extra = " در این سناریو، مناطق قابل استطاعت عمدتا در بخش‌های کم‌هزینه‌تر جنوب و جنوب شرقی تهران قرار دارند — توان پرداخت، جغرافیا دارد.";
      }
    }
    var txt = "سناریوی خانوار فرضی: درآمد " + u.toFaDigits(MAP.mult) + " برابر حداقل دستمزد قانونی سال " + u.toFaDigits(MAP.year) +
      " (حدود " + mwT + ")؛ خانه " + u.toFaDigits(MAP.size) + " متری؛ سقف سهم اجاره " + u.toFaDigits(MAP.share) + "٪ از درآمد. " +
      u.toFaDigits(n) + " منطقه از " + u.toFaDigits(22) + " منطقه داخل توان اجاره‌اند." + extra;
    el("map-note").textContent = txt;
  }

  function paintOne(path, isSel) {
    var r = ratioFor(path.getAttribute("data-reg"));
    path.setAttribute("fill", r == null ? "url(#hatch)" : (r <= 1 ? affColor(r) : "#39414f"));
    path.classList.toggle("sel", !!isSel);
  }

  function paintMap() {
    var paths = document.querySelectorAll("#map-svg .district");
    for (var i = 0; i < paths.length; i++) paintOne(paths[i], paths[i].getAttribute("data-reg") === MAP.selected);
  }

  function updateMap() { paintMap(); updateDetail(); }

  function updateDetail() {
    var box = el("map-detail");
    if (!MAP.selected) {
      box.innerHTML = "روی هر منطقه بزن تا جزئیاتش را ببینی. در این حالت، <b>" + u.toFaDigits(mapSummary()) + "</b> منطقه از ۲۲ منطقه داخل توان اجاره‌اند.";
      return;
    }
    var regStr = MAP.selected;
    var rent = districtRent(regStr, MAP.year);
    var budget = mapBudget();
    var name = regionName(regStr);
    if (rent == null) {
      box.innerHTML = "<b>" + name + "</b> — داده اجاره برای این سال در دسترس نیست.";
      return;
    }
    var cost = rent * MAP.size;
    var ratio = cost / budget;
    var verdict = ratio <= 1 ? "<b style='color:var(--pos)'>داخل توان اجاره</b>" : "<b style='color:#c98d8a'>خارج از توان اجاره</b>";
    box.innerHTML = "<b>" + name + "</b> · سال " + u.toFaDigits(MAP.year) + " · اجاره ~" + u.toFaDigits(rent) +
      " تومان/متر · " + u.toFaDigits(MAP.size) + " متری ≈ " + u.faCompact(cost, "تومان") + " در ماه · نسبت به بودجه اجاره: " +
      u.toFaDigits(Math.round(ratio * 100) / 100) + "× → " + verdict;
  }

  /* ============================================================
     FIGURE 5 — commute fuel calculator
     ============================================================ */
  var CALC = { km: 100, eff: 9, price: 3000, wage: 6 };

  function calcOutputs(o) {
    o = o || CALC;
    var kmM = o.km * 22;
    var LM = kmM * o.eff / 100;
    var cost = LM * o.price;
    var share = cost / (o.wage * 1e6) * 100;
    return { kmM: kmM, L: LM, cost: cost, share: share };
  }

  function buildCalc() {
    var effHost = el("calc-eff");
    effHost.innerHTML = "";
    [7, 9, 12].forEach(function (e) {
      var b = u.h("button", { type: "button", "class": "chip" + (e === CALC.eff ? " active" : ""), "data-eff": e }, u.toFaDigits(e) + " لیتر/۱۰۰km");
      b.addEventListener("click", function () {
        CALC.eff = e;
        var cs = effHost.children;
        for (var i = 0; i < cs.length; i++) cs[i].classList.toggle("active", +cs[i].getAttribute("data-eff") === CALC.eff);
        renderCalc();
      });
      effHost.appendChild(b);
    });
    el("calc-km").addEventListener("input", function () { CALC.km = +el("calc-km").value; renderCalc(); });
    el("calc-price").addEventListener("input", function () { CALC.price = +el("calc-price").value; renderCalc(); });
    el("calc-wage").addEventListener("input", function () { CALC.wage = +el("calc-wage").value; renderCalc(); });
    renderCalc();
  }

  function renderCalc() {
    el("calc-km").value = CALC.km;
    el("calc-price").value = CALC.price;
    el("calc-wage").value = CALC.wage;
    el("calc-km-lbl").textContent = u.toFaDigits(CALC.km) + " km";
    el("calc-price-lbl").textContent = u.fa(CALC.price) + " تومان";
    el("calc-wage-lbl").textContent = u.fa(CALC.wage) + " میلیون";

    var o = calcOutputs();
    var Llow = CALC.km * 22 * 7 / 100;
    var Lhigh = CALC.km * 22 * 12 / 100;

    el("calc-cards").innerHTML =
      '<div class="calc-card"><div class="l">مسافت ماهانه (۲۲ روز کاری)</div><div class="v">' + u.toFaDigits(o.kmM) + ' <small>km</small></div></div>' +
      '<div class="calc-card hot"><div class="l">بنزین رفت‌وآمدِ کار در ماه</div><div class="v">' + u.toFaDigits(Math.round(o.L)) + ' <small>لیتر</small></div></div>' +
      '<div class="calc-card"><div class="l">هزینه سوخت در ماه</div><div class="v">' + u.faCompact(o.cost, "تومان") + "</div></div>" +
      '<div class="calc-card hot"><div class="l">سهم سوخت از درآمد</div><div class="v">' + u.faPct(o.share, 1) + "</div></div>";

    el("calc-burden-fill").style.width = Math.min(o.share, 100).toFixed(1) + "%";
    el("calc-note").textContent =
      "سناریوی امروزی (خانوار فرضی): درآمد " + u.toFaDigits(CALC.wage) + " میلیون تومان/ماه؛ " + u.toFaDigits(CALC.eff) +
      " لیتر/۱۰۰km؛ ۲۲ روز کاری. با ۷ تا ۱۲ لیتر، ماهانه بین " + u.toFaDigits(Math.round(Llow)) + " تا " +
      u.toFaDigits(Math.round(Lhigh)) + " لیتر. رابطه این درآمد نمونه با حداقل دستمزد در روش‌شناسی پایان گزارش. — محاسبه بر اساس داده و فرض‌های اعلام‌شده";
  }

  /* ============================================================
     FIGURE 6 — price-shock interaction (price × eff × income)
     ============================================================ */
  var SHOCK = { prices: [3000, 6000, 9000, 15000, 30000], idx: 0, eff: 9, wage: 6, svg: null };

  function shockCalc(p) {
    var kmM = 100 * 22;
    var LM = kmM * SHOCK.eff / 100;
    var cost = LM * p;
    var share = cost / (SHOCK.wage * 1e6) * 100;
    return { cost: cost, share: share, L: LM };
  }

  function drawShock() {
    var W = 720, H = 380, pl = 40, pr = 16, pt = 34, pb = 48;
    var iw = W - pl - pr, ih = H - pt - pb;
    var vmax = 120;
    var n = SHOCK.prices.length;
    var slot = iw / n;
    var barW = slot * 0.56;

    var host = el("shock-chart");
    if (!SHOCK.svg) {
      SHOCK.svg = u.svgEl("svg", { "class": "g-chart", role: "img", "aria-label": "هزینه رفت‌وآمد با افزایش قیمت بنزین" });
      host.appendChild(SHOCK.svg);
    }
    var svg = SHOCK.svg;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.innerHTML = "";

    // reference line 30%
    [30, 60, 90].forEach(function (vv) {
      var y = pt + (1 - vv / vmax) * ih;
      svg.appendChild(u.svgEl("line", { x1: pl, x2: W - pr, y1: y, y2: y, "class": "grid-line" }));
      var t = u.svgEl("text", { x: pl - 8, y: y + 4, "class": "axis-txt", "text-anchor": "end" });
      t.textContent = u.toFaDigits(vv) + "٪";
      svg.appendChild(t);
    });
    var y30 = pt + (1 - 30 / vmax) * ih;
    svg.appendChild(u.svgEl("line", { x1: pl, x2: W - pr, y1: y30, y2: y30, stroke: "#7fb7ff", "stroke-dasharray": "3 5", "stroke-width": 1 }));
    var t30 = u.svgEl("text", { x: W - pr - 4, y: y30 - 6, "class": "axis-txt", "text-anchor": "end", fill: "#7fb7ff", "font-size": "11" });
    t30.textContent = "آستانه ۳۰٪ (خط مرجع)";
    svg.appendChild(t30);

    SHOCK.prices.forEach(function (p, i) {
      var o = shockCalc(p);
      var share = o.share;
      var x = pl + i * slot + (slot - barW) / 2;
      var h = Math.min(share, vmax) / vmax * ih;
      var y = pt + ih - h;
      var sel = i === SHOCK.idx;
      var rect = u.svgEl("rect", { x: x, y: y, width: barW, height: h, rx: 4, fill: sel ? "#f2b632" : "#3b4353", opacity: sel ? 1 : 0.65, style: "cursor:pointer", "data-i": i });
      svg.appendChild(rect);
      var tv = u.svgEl("text", { x: x + barW / 2, y: Math.max(y - 6, pt + 10), "text-anchor": "middle", "class": "axis-txt", "font-size": "12", fill: sel ? "#f2b632" : "#a4aeba", "font-weight": "700" });
      var pctStr = share > 99 ? u.toFaDigits(Math.round(share)) + "٪" : u.faPct(share, 1);
      tv.textContent = pctStr;
      svg.appendChild(tv);
      var tl = u.svgEl("text", { x: x + barW / 2, y: H - 10, "text-anchor": "middle", "class": "axis-txt", "font-size": "11" });
      tl.textContent = i === 0 ? "پایه" : "×" + u.toFaDigits(p / SHOCK.prices[0]);
      svg.appendChild(tl);
      var tp = u.svgEl("text", { x: x + barW / 2, y: H - 26, "text-anchor": "middle", "class": "axis-txt", "font-size": "10", fill: "#6c7788" });
      tp.textContent = u.fa(p) + " تومان";
      svg.appendChild(tp);
    });

    // y-axis title
    var yt = u.svgEl("text", { x: 12, y: pt + ih / 2, "class": "axis-txt", "font-size": "11", transform: "rotate(-90 12 " + (pt + ih / 2) + ")", "text-anchor": "middle", fill: "#6c7788" });
    yt.textContent = "سهم سوخت از حقوق ماهانه";
    svg.appendChild(yt);

    updateShockNote();
  }

  function updateShockNote() {
    var p = SHOCK.prices[SHOCK.idx];
    var o = shockCalc(p);
    el("shock-price").value = SHOCK.idx;
    el("shock-price-lbl").textContent = (SHOCK.idx === 0 ? "پایه · " : "×" + u.toFaDigits(p / SHOCK.prices[0]) + " · ") + u.fa(p) + " تومان/لیتر";
    el("shock-wage-lbl").textContent = u.fa(SHOCK.wage) + " میلیون";
    el("shock-note").textContent =
      "مسافت ثابت: ۱۰۰ km/day · مصرف " + u.toFaDigits(SHOCK.eff) + " لیتر/۱۰۰km · درآمد " + u.toFaDigits(SHOCK.wage) +
      " میلیون تومان/ماه. هزینه ماهانه سوخت: " + u.faCompact(o.cost, "تومان") +
      " · معادل " + u.faPct(o.share, 1) + " از درآمد — محاسبه/سناریو.";
  }

  function buildShock() {
    // efficiency chips
    var effHost = el("shock-eff");
    effHost.innerHTML = "";
    [7, 9, 12].forEach(function (e) {
      var b = u.h("button", { type: "button", "class": "chip" + (e === SHOCK.eff ? " active" : ""), "data-eff": e }, u.toFaDigits(e) + " لیتر");
      b.addEventListener("click", function () {
        SHOCK.eff = e;
        var cs = effHost.children;
        for (var i = 0; i < cs.length; i++) cs[i].classList.toggle("active", +cs[i].getAttribute("data-eff") === SHOCK.eff);
        drawShock();
      });
      effHost.appendChild(b);
    });
    el("shock-price").addEventListener("input", function () { SHOCK.idx = +el("shock-price").value; drawShock(); });
    el("shock-wage").addEventListener("input", function () { SHOCK.wage = +el("shock-wage").value; drawShock(); });
    el("shock-chart").addEventListener("click", function (e) {
      var r = e.target.closest ? e.target.closest("rect[data-i]") : null;
      if (r) { SHOCK.idx = +r.getAttribute("data-i"); drawShock(); }
    });
    drawShock();
  }

  /* ============================================================
     Reveal, hero, sources
     ============================================================ */
  function initReveal() {
    var els = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(els, function (x) { x.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.15 });
    Array.prototype.forEach.call(els, function (x) { io.observe(x); });
  }

  function renderHeroStats() {
    var gas = u.numKeys(D.annual.gasoline);
    var years = Object.keys(gas).map(Number).sort(function (a, b) { return a - b; });
    var y0 = years[0], yLast = years[years.length - 1];
    var g0 = gas[y0], g1 = gas[yLast];
    var strip = el("hero-stats");
    var items = [
      { n: u.toFaDigits(g1), l: "میلیون لیتر بنزین در روز (" + u.toFaDigits(yLast) + ") — وزارت نفت/شانا" },
      { n: u.toFaDigits(Math.round(g1 / g0 * 10) / 10) + "×", l: "مصرف روزانه نسبت به سال " + u.toFaDigits(y0) },
      { n: "۳۰–۴۰ هزار", l: "مسافر روزانه بین پرند و تهران (برآورد گزارش‌ها)" },
      { n: "~۱۰۰ km", l: "رفت‌وبرگشت روزانه در سناریوی پرند" }
    ];
    strip.innerHTML = items.map(function (it) {
      return '<div class="hero-stat"><span class="n">' + it.n + "</span><span class='l'>" + it.l + "</span></div>";
    }).join("");
  }

  function renderSources() {
    var list = el("src-list");
    list.innerHTML = "";
    var order = ["S1", "S4", "S2", "S3", "S5", "S6", "S7", "S8", "S9", "C1"];
    order.forEach(function (id) {
      var s = D.sources[id];
      if (!s) return;
      var li = u.h("li", null,
        "<b>" + s.title + "</b> <span class='grade'>" + id + "</span>" +
        "<div class='srow'>" + (s.url ? '<a href="' + s.url + '" target="_blank" rel="noopener">' + s.url + "</a>" : "") +
        (s.accessed_date ? " · دسترسی " + s.accessed_date : "") + "</div>" +
        (s.notes ? "<div class='srow'>" + s.notes + "</div>" : ""));
      list.appendChild(li);
    });
  }

  G.views = {
    drawGas: drawGas,
    drawPeriMap: drawPeriMap,
    drawParandRoute: drawParandRoute,
    drawRentWageIndex: drawRentWageIndex,
    buildMap: buildMap,
    buildCalc: buildCalc,
    buildShock: buildShock,
    initReveal: initReveal,
    renderHeroStats: renderHeroStats,
    renderSources: renderSources
  };
})(window.GH = window.GH || {});
