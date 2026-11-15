#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera el PWA autocontenido del Bridge Hipertrofia 2W (Nordic Wellness).

Uso:  python3 build_bridge_2w.py      (requiere `npm install` previo: jsdom)

Escribe bridge_hipertrofia_2w_v{VERSION}.html, index.html (copia idéntica) y sw.js,
y ejecuta todas las validaciones. Si alguna falla, sale con código 1.

Convenciones: datos en `const P = [...];\n` dentro del HTML, cada replace precedido
de `assert a in s`, service worker real (sw.js), router con navStack explícito.
"""
import datetime, json, os, re, subprocess, sys, tempfile

CAP = 50
VERSION = 1
START = datetime.date(2026, 11, 16)          # lunes de la semana 1
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = f"bridge_hipertrofia_2w_v{VERSION}.html"
INDEX = "index.html"
SW = "sw.js"
CACHE_PREFIX = "bridge2w-"
CACHE = f"{CACHE_PREFIX}v{VERSION}"
# Claves y nombres de la app principal (mismo origen en GitHub Pages): no pueden aparecer.
FORBIDDEN = ["p12w", "p16w", "rebuild-strong", "rebuild_strong", "rebuildstrong"]

# ---------------------------------------------------------------------------
# Datos. Cada item: code, ex, sets, load (S1), load2 (S2, opcional),
# rir (S1), rir2 (S2), tech (S1), tech2 (S2), rest.
# Tipos de bloque: warm | main | hyp | tech | z2 | cool
# ---------------------------------------------------------------------------
def it(code, ex, sets, load="", rir="", tech="", rest="", load2=None, rir2=None, tech2=None):
    return dict(code=code, ex=ex, sets=sets, load=load, load2=load2 if load2 is not None else load,
                rir=rir, rir2=rir2 if rir2 is not None else rir, tech=tech,
                tech2=tech2 if tech2 is not None else tech, rest=rest)

def blk(name, mins, typ, items, note=""):
    return dict(name=name, min=mins, type=typ, items=items, note=note)

COOL = lambda m: blk("Transiciones + vuelta a la calma", m, "cool", [], "Ajuste de máquinas, cambios de discos y 3–5' de movilidad final.")

SESSIONS = [
  dict(id="D1", day="Lunes", title="Lower A", focus="Cuádriceps", tech="Widowmaker + lengthened partials", blocks=[
    blk("Calentamiento", 5, "warm", [it("W", "Bike Erg 3' + movilidad cadera/tobillo", "—", rir="Suave")]),
    blk("A · Back Squat", 11, "main", [it("A", "Back Squat", "3 × 6", "110 kg (76 %)", "RIR 2", rest="2'30\"", load2="115 kg (79 %)", rir2="RIR 1–2")], "Incluye rampas: barra, 60, 80, 95 kg."),
    blk("A+ · Widowmaker", 4, "tech", [it("A+", "Back Squat widowmaker", "1 × 20", "85–90 kg", "Respirando entre reps", load2="90–95 kg")]),
    blk("B · Hack squat", 9, "hyp", [it("B", "Hack squat", "3 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Última: lengthened partials", rest="90\"")]),
    blk("C · Superserie", 8, "hyp", [
      it("C1", "Leg extension", "3 × 12–15", rir="RIR 1", rir2="RIR 0", tech="Última: drop", tech2="Última: drop doble"),
      it("C2", "Seated leg curl", "3 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Última: drop", rest="60\"")]),
    blk("D · Gemelo", 4, "hyp", [it("D", "Standing calf raise", "3 × 10–12", tech="Pausa 2\" en estiramiento", rir="RIR 1", rir2="RIR 0", rest="45\"")]),
    COOL(9)]),
  dict(id="D2", day="Martes", title="Upper A", focus="Horizontal · pecho / espalda media", tech="Rest-pause + myo-reps", blocks=[
    blk("Calentamiento", 4, "warm", [it("W", "Row Erg 2' + rotaciones externas con banda", "—", rir="Suave")]),
    blk("A · Superserie antagonista", 14, "main", [
      it("A1", "Bench Press", "4 × 6–8", "92,5 kg (74 %)", "RIR 2", rest="75\"", load2="95 kg (76 %)", rir2="RIR 1–2"),
      it("A2", "Chest-supported row (T-bar o máquina)", "4 × 8–10", rir="RIR 2", rir2="RIR 1–2", rest="75\"")], "Incluye rampas de banca."),
    blk("B · Superserie", 10, "hyp", [
      it("B1", "Incline DB press (30°)", "3 × 8–10", rir="RIR 1", rir2="RIR 0", tech="Última: rest-pause", rest="60\""),
      it("B2", "Remo unilateral en polea", "3 × 10–12", rir="RIR 1", rir2="RIR 0", rest="60\"")]),
    blk("C · Pec deck myo-reps", 4, "tech", [it("C", "Pec deck", "1 serie myo-reps", tech="15 + 4×5", tech2="15 + 5×5")]),
    blk("D · Deltoides", 6, "hyp", [
      it("D1", "Reverse pec deck", "3 × 15", rir="RIR 1", rir2="RIR 0"),
      it("D2", "Elevación lateral en polea", "3 × 12–15", rir="RIR 1", rir2="RIR 0", rest="45\"")]),
    blk("E · Brazos", 5, "hyp", [
      it("E1", "Extensión tríceps overhead en polea", "2 × 10–12", rir="RIR 1", rir2="RIR 0"),
      it("E2", "Curl inclinado con mancuernas", "2 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Última: drop", rest="45\"")]),
    COOL(7)]),
  dict(id="D3", day="Miércoles", title="Brazos + deltoides", focus="Especialización con volumen extra", tech="Mechanical drop + drop doble", blocks=[
    blk("Calentamiento", 3, "warm", [it("W", "Dips y dominadas sin lastre, 1×5 de cada", "—")]),
    blk("A · Superserie lastrada", 12, "main", [
      it("A1", "Weighted dip", "4 × 6–8", "+15 kg", "RIR 2", rest="60\"", load2="+17,5 kg", rir2="RIR 1–2"),
      it("A2", "Weighted chin-up supino", "4 × 6–8", "+10 kg", "RIR 2", rest="60\"", load2="+12,5 kg", rir2="RIR 1–2")]),
    blk("B · Press de hombro", 7, "hyp", [it("B", "Press de hombro sentado con mancuernas", "3 × 8–10", rir="RIR 1", rir2="RIR 0", tech="Última: rest-pause", rest="75\"")]),
    blk("C · Lateral mechanical drop", 5, "tech", [it("C", "Elevación lateral con mancuernas", "3 rondas", tech="Estricta al fallo → inercia controlada al fallo → parciales", rest="60\"")]),
    blk("D · Brazos I", 7, "hyp", [
      it("D1", "Curl predicador EZ", "3 × 10", rir="RIR 1", rir2="RIR 0", tech="Última: drop", tech2="Última: drop doble"),
      it("D2", "Pushdown en polea", "3 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Última: drop", tech2="Última: drop doble", rest="45\"")]),
    blk("E · Brazos II", 7, "hyp", [
      it("E1", "Curl martillo con cuerda en polea", "3 × 12", rir="RIR 1", rir2="RIR 0", tech="Última: myo-reps"),
      it("E2", "Extensión overhead con mancuerna", "3 × 12", rir="RIR 1", rir2="RIR 0", tech="Última: myo-reps", rest="45\"")]),
    blk("F · Deltoide posterior", 4, "tech", [it("F", "Reverse pec deck", "2 × 15", rir="RIR 0", tech="Última: lengthened partials", rest="45\"")]),
    COOL(5)]),
  dict(id="D4", day="Jueves", title="Lower B", focus="Cadena posterior / glúteo", tech="Rest-pause 20 reps + drop", blocks=[
    blk("Calentamiento", 4, "warm", [it("W", "Bike Erg 2' + bisagras con PVC + puente de glúteo", "—", rir="Suave")]),
    blk("A · Romanian Deadlift", 12, "main", [it("A", "Romanian Deadlift", "4 × 8", "115–120 kg", "RIR 2", rest="2'", load2="120–125 kg", rir2="RIR 1–2")], "Incluye rampas."),
    blk("B · Prensa rest-pause", 9, "tech", [it("B", "Prensa (pies altos)", "3 × 12–15", rir="RIR 1", rir2="RIR 0", tech="Última: rest-pause hasta 20 reps totales", rest="90\"")]),
    blk("C · Superserie", 8, "hyp", [
      it("C1", "Lying leg curl", "3 × 8–10", rir="RIR 1", rir2="RIR 0", tech="Última: drop", tech2="Última: drop doble"),
      it("C2", "Hip thrust (máquina o barra)", "3 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Pausa 1\" arriba", rest="60\"")]),
    blk("D · Zancadas", 5, "hyp", [it("D", "Zancadas caminando con mancuernas", "2 × 20 pasos", "2 × 20–22,5 kg", "RIR 2", rest="75\"", load2="2 × 22,5–25 kg", rir2="RIR 1")]),
    blk("E · Gemelo", 4, "hyp", [it("E", "Seated calf raise", "3 × 15–20", rir="RIR 0", rest="45\"")]),
    COOL(8)]),
  dict(id="D5", day="Viernes", title="Upper B", focus="Vertical · hombro / dorsal", tech="Lengthened partials + myo-reps", blocks=[
    blk("Calentamiento", 4, "warm", [it("W", "Ski Erg 2' + face pulls ligeros", "—", rir="Suave")]),
    blk("A · Superserie antagonista", 14, "main", [
      it("A1", "Strict Press", "4 × 6–8", "55 kg (73 %)", "RIR 2", rest="75\"", load2="57,5 kg (77 %)", rir2="RIR 1–2"),
      it("A2", "Weighted pull-up prono", "4 × 6–8", "+10 kg", "RIR 2", rest="75\"", load2="+12,5 kg", rir2="RIR 1–2")], "Incluye rampas de press."),
    blk("B · Superserie", 9, "hyp", [
      it("B1", "Lat pulldown", "3 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Última: lengthened partials"),
      it("B2", "Chest press en máquina", "3 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Última: drop", tech2="Última: drop doble", rest="60\"")]),
    blk("C · Deltoides", 6, "tech", [
      it("C1", "Elevación lateral en máquina", "3 × 12–15", tech="Última: myo-reps", rir="RIR 1", rir2="RIR 0"),
      it("C2", "Face pull", "3 × 15", rir="RIR 1", rir2="RIR 0", rest="45\"")]),
    blk("D · Brazos en estiramiento", 6, "hyp", [
      it("D1", "Bayesian curl en polea", "3 × 10–12", rir="RIR 1", rir2="RIR 0"),
      it("D2", "Skull crusher EZ (barra tras la cabeza)", "3 × 10–12", rir="RIR 1", rir2="RIR 0", tech="Última: drop", tech2="Última: drop doble", rest="45\"")]),
    COOL(11)]),
  dict(id="D6", day="Sábado", title="Zona 2 larga", focus="Única Z2 de la semana", tech="Aeróbico continuo", optional=True, blocks=[
    blk("Calentamiento", 3, "warm", [it("W", "Bike Erg progresivo", "3'", tech="Subiendo ritmo")]),
    blk("A · Zona 2", 42, "z2", [it("A", "Bike Erg continuo", "42'", "~420–430 m/min", tech="Banda Polar en Z2")], "Tu marca · BTWB: Z2 bike ~420–430 m/min."),
    blk("Vuelta a la calma", 5, "cool", [it("C", "Movilidad", "5'")]),
  ]),
]

RULES = dict(
  weeks=[
    dict(w=1, name="Acumulación", lines=["Compuestos RIR 2–3", "Máquinas / aislamiento RIR 1", "Técnicas solo en la última serie", "Cargas indicadas"]),
    dict(w=2, name="Intensificación", lines=["Compuestos RIR 1–2", "Máquinas / aislamiento RIR 0 (fallo técnico)", "Técnicas intensificadas (drop doble, más mini-series)", "+2,5–5 % en compuestos si S1 salió en el RIR objetivo", "Mismas series: se progresa por intensidad, no por volumen"]),
  ],
  glossary=[
    ["Myo-reps", "Serie de activación a RIR 1 (12–15 reps), 3–5 respiraciones, mini-series de 3–5 reps hasta que no salgan."],
    ["Rest-pause", "Serie a RIR 0, 15 s de pausa, repetir 2 veces más."],
    ["Lengthened partials", "Al fallo, medias repeticiones en la mitad estirada del recorrido hasta fallo."],
    ["Drop set", "Al fallo, bajar ~25 % la carga y seguir al fallo (S2: drop doble)."],
    ["Mechanical drop", "Cambiar a una variante mecánicamente más fácil sin descanso."],
    ["Widowmaker", "1 serie de 20 reps con carga de ~10RM, respirando entre reps."],
  ],
  recovery=["Superávit +300–500 kcal/día", "Proteína ~2 g/kg → ~185 g/día en 4–5 tomas", "Creatina monohidrato 5 g/día",
            "Sueño: con despertador antes de las 5:00, a la cama a las 21:30", "Domingo: 20' de yoga/movilidad",
            "Vuelta al box: semana 1 con volumen −30 % y RIR 2–3"],
)

# ---------------------------------------------------------------------------
# Derivados del build: totales, fechas, códigos de sesión y nº de series
# ---------------------------------------------------------------------------
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

def n_sets(sets):
    """Nº de series registrables a partir de `sets`; 0 = sin registro."""
    if sets == "—" or re.fullmatch(r"\d+'", sets):
        return 0
    m = (re.match(r"(\d+) × \S", sets) or re.fullmatch(r"(\d+) rondas", sets)
         or re.match(r"(\d+) series? ", sets))
    assert m, f"sets no reconocido: {sets!r}"
    n = int(m.group(1))
    assert 1 <= n <= 10, f"nº de series fuera de rango: {sets!r}"
    return n

for s in SESSIONS:
    tot = sum(b["min"] for b in s["blocks"])
    assert tot <= CAP, f"{s['id']} = {tot}' > {CAP}'"
    s["total"] = tot
    codes = [i["code"] for b in s["blocks"] for i in b["items"]]
    assert len(codes) == len(set(codes)), f"{s['id']}: códigos de ejercicio repetidos"
z2_days = [s["id"] for s in SESSIONS if any(b["type"] == "z2" for b in s["blocks"])]
assert z2_days == ["D6"], z2_days
assert sum(1 for s in SESSIONS if not s.get("optional")) == 5
assert [s["id"] for s in SESSIONS] == [f"D{d}" for d in range(1, 7)]
assert [s["day"] for s in SESSIONS] == DAYS

def week_view(w):
    out = []
    for d, s in enumerate(SESSIONS, 1):
        date = START + datetime.timedelta(days=(w - 1) * 7 + (d - 1))
        ss = {k: v for k, v in s.items() if k != "blocks"}
        ss["code"] = f"BRG-S{w}-D{d}"
        ss["date"] = date.isoformat()
        ss["dlabel"] = f"{s['day'][:3].lower()} {date.day:02d}/{date.month:02d}"
        ss["dfull"] = f"{s['day']} {date.day:02d}/{date.month:02d}/{date.year}"
        ss["blocks"] = []
        for b in s["blocks"]:
            bb = {k: v for k, v in b.items() if k != "items"}
            bb["items"] = [dict(code=i["code"], ex=i["ex"], sets=i["sets"],
                                load=i["load"] if w == 1 else i["load2"],
                                rir=i["rir"] if w == 1 else i["rir2"],
                                tech=i["tech"] if w == 1 else i["tech2"],
                                rest=i["rest"], n=n_sets(i["sets"])) for i in b["items"]]
            ss["blocks"].append(bb)
        out.append(ss)
    return out

def week(w):
    a = START + datetime.timedelta(days=(w - 1) * 7)
    z = a + datetime.timedelta(days=6)
    return dict(week=w, name=RULES["weeks"][w-1]["name"], start=a.isoformat(), end=z.isoformat(),
                range=f"{a.day}–{z.day}/{a.month:02d}", sessions=week_view(w))

P = [week(w) for w in (1, 2)]
DATA = json.dumps(P, ensure_ascii=False)
RDATA = json.dumps(RULES, ensure_ascii=False)
assert "</script" not in (DATA + RDATA).lower()
assert "\n" not in DATA

# ---------------------------------------------------------------------------
# Service worker (sw.js): alcance ./, caché propia, solo toca cachés bridge2w-*
# ---------------------------------------------------------------------------
SW_JS = r"""// Generado por build_bridge_2w.py. No editar a mano.
// Alcance ./ (solo este repo). Comparte origen con otras apps: solo usa y borra
// cachés cuyo nombre empieza por PREFIX.
const PREFIX = "__PREFIX__";
const CACHE = "__CACHE__";
const SHELL = ["./", "./index.html"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Stale-while-revalidate: responde desde la caché propia y la refresca en segundo plano.
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (!req.url.startsWith(self.registration.scope)) return;
  e.respondWith(
    caches.open(CACHE).then(c =>
      c.match(req, {ignoreSearch: true}).then(hit => {
        const net = fetch(req).then(res => {
          if (res && res.ok) c.put(req, res.clone());
          return res;
        });
        if (hit) { e.waitUntil(net.catch(() => {})); return hit; }
        return net.catch(() => c.match("./index.html").then(r => r || Response.error()));
      })
    )
  );
});
"""
for a, b in (("__PREFIX__", CACHE_PREFIX), ("__CACHE__", CACHE)):
    assert a in SW_JS
    SW_JS = SW_JS.replace(a, b)

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Bridge 2W">
<meta name="theme-color" content="#0d0f13">
<title>Bridge Hipertrofia · 2 semanas · Nordic Wellness</title>
<style>
:root{
  --bg:#0d0f13; --panel:#161a21; --panel2:#1c222b; --line:#28303c;
  --ink:#eef2f7; --mut:#8b97a8; --dim:#5c6675;
  --accent:#f2a33c; --accentink:#0d0f13;
  --b1:#4f8cff; --b2:#26c1a3; --b3:#f2a33c; --b4:#e0556b;
  --alactic:#e0556b; --wod:#c77dff; --zone2:#f4c430; --lactic:#4ec36b; --vo2:#4f8cff; --skill:#9aa4b2;
  --t-warm:var(--skill); --t-main:var(--b1); --t-hyp:var(--b2); --t-tech:var(--b4); --t-z2:var(--zone2); --t-cool:var(--dim);
  --topbar:64px; --safe:env(safe-area-inset-top,0px);
  --f-body:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --f-disp:"Avenir Next Condensed","HelveticaNeue-CondensedBold","Roboto Condensed","Arial Narrow","Franklin Gothic Medium Cond",sans-serif-condensed,var(--f-body);
  --f-mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:var(--f-body);-webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%}
body{padding-bottom:calc(40px + env(safe-area-inset-bottom,0px))}
h1,h2,h3,.disp{font-family:var(--f-disp);font-stretch:condensed;letter-spacing:.01em;margin:0}
.mono{font-family:var(--f-mono)}
#topbar{position:fixed;top:0;left:0;right:0;z-index:50;height:calc(var(--topbar) + var(--safe));padding-top:var(--safe);
  background:rgba(13,15,19,.92);backdrop-filter:saturate(140%) blur(10px);-webkit-backdrop-filter:saturate(140%) blur(10px);
  border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px;padding-left:14px;padding-right:14px}
#topbar .back{width:36px;height:36px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--ink);
  font-size:20px;display:flex;align-items:center;justify-content:center;cursor:pointer}
#topbar .back[hidden]{display:none}
#topbar .tt{flex:1;min-width:0}
#topbar .tt h1{font-size:22px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#topbar .tt small{display:block;color:var(--mut);font-size:11px;letter-spacing:.08em;text-transform:uppercase}
#topbar .ver{font-family:var(--f-mono);font-size:11px;color:var(--accent);border:1px solid var(--accent);border-radius:6px;padding:2px 6px}
#spacer{height:calc(var(--topbar) + var(--safe))}
main{max-width:720px;margin:0 auto;padding:16px 14px}
.mission{font-family:var(--f-disp);font-stretch:condensed;font-size:20px;font-weight:600;line-height:1.2;color:var(--ink);
  border-left:3px solid var(--accent);padding:4px 0 4px 12px;margin:4px 0 18px}
.tabs{display:flex;gap:8px;margin-bottom:14px}
.tab{flex:1;padding:10px 8px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:var(--mut);
  font-family:var(--f-disp);font-stretch:condensed;font-size:17px;font-weight:600;text-align:center;cursor:pointer}
.tab b{display:block;font-family:var(--f-body);font-stretch:normal;font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase}
.tab.on{background:var(--accent);color:var(--accentink);border-color:var(--accent)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px;margin-bottom:10px}
.card.today{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.day{display:flex;gap:12px;align-items:center}
.day[data-id]{cursor:pointer}
.day .badge{width:48px;height:48px;border-radius:12px;background:var(--panel2);display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-family:var(--f-disp);font-stretch:condensed;font-weight:700;font-size:18px;flex:none}
.day .badge small{font-size:10px;color:var(--mut);font-family:var(--f-body);font-stretch:normal;font-weight:500}
.today .badge{background:var(--accent);color:var(--accentink)}
.today .badge small{color:var(--accentink)}
.day .meta{flex:1;min-width:0}
.day h3{font-size:20px;font-weight:700}
.day p{margin:2px 0 0;color:var(--mut);font-size:13px}
.day p.cd{font-family:var(--f-mono);font-size:11px;color:var(--dim);margin-top:4px}
.day .min{font-family:var(--f-mono);font-size:13px;color:var(--ink);text-align:right}
.day .min small{display:block;color:var(--dim);font-size:10px}
.opt,.hoy{font-family:var(--f-body);font-stretch:normal;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--zone2);border:1px solid var(--zone2);border-radius:5px;padding:1px 5px;margin-left:6px;vertical-align:middle}
.hoy{color:var(--accentink);background:var(--accent);border-color:var(--accent);font-weight:600}
.bar{display:flex;height:10px;border-radius:6px;overflow:hidden;background:var(--panel2);margin-top:10px}
.bar i{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 4px;font-size:11px;color:var(--mut)}
.legend span::before{content:"";display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:5px;background:var(--c);vertical-align:-1px}
.sec{font-family:var(--f-disp);font-stretch:condensed;font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);margin:20px 2px 8px}
.blk{border-left:4px solid var(--c);padding:12px 14px}
.blk .hd{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.blk h3{font-size:19px;font-weight:700}
.blk .m{font-family:var(--f-mono);font-size:13px;color:var(--c)}
.blk .note{color:var(--mut);font-size:12px;margin:4px 0 0}
.ex{display:grid;grid-template-columns:34px 1fr;gap:4px 10px;padding:10px 0 0;margin-top:10px;border-top:1px solid var(--line)}
.ex:first-of-type{border-top:none;margin-top:6px;padding-top:4px}
.ex .code{font-family:var(--f-mono);font-weight:700;color:var(--c);font-size:13px;padding-top:2px}
.ex .nm{font-weight:600;font-size:15px}
.chips{grid-column:2;display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:12px;border-radius:7px;padding:3px 7px;background:var(--panel2);color:var(--ink)}
.chip.k{font-family:var(--f-mono)}
.chip.t{background:transparent;border:1px solid var(--c);color:var(--c)}
.chip.r{color:var(--mut)}
.log{grid-column:2;display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:6px 10px;margin-top:6px}
.set{display:flex;align-items:center;gap:5px;min-width:0}
.set .sn{font-family:var(--f-mono);font-size:11px;color:var(--dim);width:12px;flex:none;text-align:right}
.set .x{color:var(--dim);font-size:13px;flex:none}
.in{min-width:0;height:38px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink);
  font-family:var(--f-mono);font-size:16px;text-align:center;padding:0 4px;-webkit-appearance:none;appearance:none}
.in.kg{flex:1.3 1 0}
.in.reps{flex:1 1 0}
.in::placeholder{color:var(--dim);font-size:12px}
.in:focus{outline:none;border-color:var(--accent)}
.in.has{border-color:var(--c)}
.btn{display:block;width:100%;padding:14px;border-radius:14px;border:none;background:var(--accent);color:var(--accentink);
  font-family:var(--f-disp);font-stretch:condensed;font-size:19px;font-weight:700;cursor:pointer;margin-top:14px}
.btn.ghost{background:var(--panel);color:var(--ink);border:1px solid var(--line)}
.warn{color:var(--zone2);font-size:12px;border:1px solid var(--zone2);border-radius:10px;padding:8px 10px;margin:0 0 10px}
.warn[hidden]{display:none}
.hint{color:var(--dim);font-size:11px;margin:6px 2px 0;text-align:center}
.manual{display:block;width:100%;min-height:150px;margin-top:10px;border-radius:12px;border:1px solid var(--line);background:var(--bg);
  color:var(--ink);font-family:var(--f-mono);font-size:12px;padding:10px}
.kv{display:grid;grid-template-columns:130px 1fr;gap:8px 12px;font-size:14px}
.kv dt{font-weight:600}
.kv dd{margin:0;color:var(--mut)}
ul.clean{margin:6px 0 0;padding-left:18px;color:var(--ink);font-size:14px;line-height:1.6}
.wk h3{font-size:19px}
.wk h3 span{color:var(--accent)}
footer{color:var(--dim);font-size:11px;text-align:center;margin-top:24px}
</style>
</head>
<body>
<header id="topbar">
  <button class="back" id="back" hidden aria-label="Atrás">‹</button>
  <div class="tt"><small id="sub">Nordic Wellness · ≤50'</small><h1 id="ttl">Bridge Hipertrofia 2W</h1></div>
  <span class="ver">B2W</span>
</header>
<div id="spacer"></div>
<main id="app"></main>
<script>
const P = __DATA__;
const R = __RULES__;
const CAP = __CAP__;
const TYPES = {warm:"Calentamiento",main:"Básico",hyp:"Hipertrofia",tech:"Técnica avanzada",z2:"Zona 2",cool:"Transición / calma"};
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* ---------- Fechas (fecha local del dispositivo) ---------- */
function todayISO(){
  const d = new Date(), p = n => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
}
function defaultWeek(t){ let w = P[0].week; P.forEach(x => { if(t >= x.start) w = x.week; }); return w; }

/* ---------- Router: navStack explícito ---------- */
const navStack = [];
let state = {view:"home", w:defaultWeek(todayISO()), id:null};

function syncURL(){
  try{ history.replaceState(null, "", "#" + state.view + (state.id ? "-" + state.id : "") + "-w" + state.w); }catch(e){}
}
function go(view, params, push){
  if(push !== false) navStack.push({...state});
  state = {...state, view, ...(params||{})};
  render();
  syncURL();
  window.scrollTo(0,0);
}
function back(){
  if(!navStack.length) return;
  const prev = navStack.pop();
  state = {...prev, w: state.w};   // la semana elegida en las pestañas se conserva
  render();
  syncURL();
  window.scrollTo(0,0);
}
function setWeek(w){ state = {...state, w}; render(); syncURL(); }
$("#back").addEventListener("click", back);

function curWeek(){ return P.find(w => w.week === state.w); }
function findSession(w, id){ return P.find(x => x.week === w).sessions.find(x => x.id === id); }

/* ---------- Registro: localStorage con clave "<código sesión>:<código ejercicio>" ---------- */
const mem = {};          // copia en memoria: la app funciona igual si el almacenamiento falla
let storageOK = true;
try{ localStorage.getItem(P[0].sessions[0].code + ":_"); }catch(e){ storageOK = false; }

const logKey = (s, i) => s.code + ":" + i.code;
function normKg(v){
  let t = String(v ?? "").replace(/,/g, ".").replace(/[^0-9.]/g, "");
  const d = t.indexOf(".");
  if(d >= 0) t = t.slice(0, d + 1) + t.slice(d + 1).replace(/\./g, "");
  t = t.replace(/\.$/, "");
  if(t.startsWith(".")) t = "0" + t;
  return t.slice(0, 7);
}
const normReps = v => String(v ?? "").replace(/[^0-9]/g, "").slice(0, 3);
const showKg = k => k.replace(".", ",");
function loadLog(key, n){
  if(mem[key] && mem[key].length === n) return mem[key];
  let v = null, raw = null;
  try{ raw = localStorage.getItem(key); }catch(e){ storageOK = false; }
  if(raw){ try{ v = JSON.parse(raw); }catch(e){ v = null; } }
  const out = [];
  for(let i = 0; i < n; i++){
    const s = Array.isArray(v) && v[i] && typeof v[i] === "object" ? v[i] : {};
    out.push({kg: normKg(s.kg), reps: normReps(s.reps)});
  }
  return (mem[key] = out);
}
function saveLog(key){
  const v = mem[key];
  try{
    if(v.some(s => s.kg || s.reps)) localStorage.setItem(key, JSON.stringify(v));
    else localStorage.removeItem(key);
    storageOK = true;
  }catch(e){ storageOK = false; }
  const w = $("#warn"); if(w) w.hidden = storageOK;
}
function realStr(log){
  let last = -1;
  log.forEach((s, i) => { if(s.kg || s.reps) last = i; });
  if(last < 0) return "";
  return log.slice(0, last + 1).map(s => (s.kg || s.reps) ? (s.kg ? showKg(s.kg) : "?") + "×" + (s.reps || "?") : "–").join(", ");
}

/* ---------- Vistas ---------- */
function bar(s){
  return '<div class="bar">' + s.blocks.map(b =>
    `<i style="width:${(b.min/CAP*100).toFixed(2)}%;background:var(--t-${b.type})" title="${esc(b.name)} · ${b.min}'"></i>`).join("") + '</div>';
}
function legend(){
  return '<div class="legend">' + Object.entries(TYPES).map(([k,v]) => `<span style="--c:var(--t-${k})">${v}</span>`).join("") + '</div>';
}
function weekTabs(){
  return '<div class="tabs">' + P.map(w =>
    `<div class="tab ${w.week===state.w?"on":""}" data-w="${w.week}">Semana ${w.week}<b>${esc(w.name)} · ${esc(w.range)}</b></div>`).join("") + '</div>';
}

function home(){
  const wk = curWeek(), today = todayISO();
  let h = '<div class="mission">Máximo estímulo hipertrófico en 50 minutos, sin perder fuerza para la vuelta al box.</div>';
  if(today > P[P.length - 1].end) h += '<p class="warn">Bridge terminado. Exporta el registro antes de borrar la app.</p>';
  h += weekTabs();
  h += wk.sessions.map(s => { const t = s.date === today; return `
    <div class="card${t?" today":""}"><div class="day" data-id="${s.id}">
      <div class="badge">${s.id}<small>${esc(s.day.slice(0,3))}</small></div>
      <div class="meta"><h3>${esc(s.title)}${s.optional?'<span class="opt">Opcional</span>':''}${t?'<span class="hoy">Hoy</span>':''}</h3><p>${esc(s.focus)} · ${esc(s.tech)}</p><p class="cd">${esc(s.code)} · ${esc(s.dlabel)}</p></div>
      <div class="min">${s.total}'<small>/ ${CAP}'</small></div>
    </div>${bar(s)}</div>`; }).join("");
  h += legend();
  h += '<button class="btn ghost" id="rules">Reglas, técnicas y recuperación</button>';
  h += '<button class="btn ghost" id="csv" data-label="Exportar todo (CSV)">Exportar todo (CSV)</button>';
  h += '<p class="hint">Copia el registro de las 2 semanas: código, fecha, ejercicio, prescrito, serie, kg, reps.</p>';
  h += '<footer>Bridge 2W · Upper/Lower ×2 + especialización · Z2 solo el sábado</footer>';
  return h;
}

function logRows(s, i){
  if(!i.n) return "";
  const key = logKey(s, i), log = loadLog(key, i.n);
  return '<div class="log">' + log.map((st, ix) => {
    const a = `autocomplete="off" autocorrect="off" spellcheck="false" data-k="${esc(key)}" data-n="${i.n}" data-i="${ix}"`;
    return `<div class="set"><span class="sn">${ix+1}</span>
      <input class="in kg${st.kg?" has":""}" type="text" inputmode="decimal" ${a} data-f="kg" placeholder="kg" aria-label="${esc(i.code)} serie ${ix+1}: carga real en kg" value="${esc(showKg(st.kg))}">
      <span class="x">×</span>
      <input class="in reps${st.reps?" has":""}" type="text" inputmode="numeric" pattern="[0-9]*" ${a} data-f="reps" placeholder="reps" aria-label="${esc(i.code)} serie ${ix+1}: reps reales" value="${esc(st.reps)}"></div>`;
  }).join("") + '</div>';
}

function session(){
  const s = findSession(state.w, state.id);
  let h = weekTabs();
  h += `<div class="card${s.date===todayISO()?" today":""}"><div class="day"><div class="badge">${s.id}<small>${esc(s.day.slice(0,3))}</small></div>
        <div class="meta"><h3>${esc(s.title)}</h3><p>${esc(s.focus)}</p><p class="cd" id="scode">${esc(s.code)} · ${esc(s.dfull)}</p></div><div class="min">${s.total}'<small>/ ${CAP}'</small></div></div>${bar(s)}${legend()}</div>`;
  h += `<p class="warn" id="warn"${storageOK?" hidden":""}>Este navegador no permite guardar datos: el registro se perderá al cerrar la app. Copia para BTWB antes de salir.</p>`;
  h += s.blocks.map(b => `
    <div class="card blk" style="--c:var(--t-${b.type})">
      <div class="hd"><h3>${esc(b.name)}</h3><span class="m">${b.min}'</span></div>
      ${b.note?`<p class="note">${esc(b.note)}</p>`:""}
      ${b.items.map(i => `
        <div class="ex"><div class="code">${esc(i.code)}</div><div class="nm">${esc(i.ex)}</div>
          <div class="chips">
            ${i.sets && i.sets!=="—" ? `<span class="chip k">${esc(i.sets)}</span>`:""}
            ${i.load?`<span class="chip k">${esc(i.load)}</span>`:""}
            ${i.rir?`<span class="chip">${esc(i.rir)}</span>`:""}
            ${i.tech?`<span class="chip t">${esc(i.tech)}</span>`:""}
            ${i.rest?`<span class="chip r">⏱ ${esc(i.rest)}</span>`:""}
          </div>${logRows(s, i)}</div>`).join("")}
    </div>`).join("");
  h += '<button class="btn" id="copy" data-label="Copiar para BTWB">Copiar para BTWB</button>';
  return h;
}

function rules(){
  let h = '<div class="sec">Progresión</div>';
  h += R.weeks.map(w => `<div class="card wk"><h3><span>S${w.w}</span> · ${esc(w.name)}</h3><ul class="clean">${w.lines.map(l=>`<li>${esc(l)}</li>`).join("")}</ul></div>`).join("");
  h += '<div class="sec">Técnicas avanzadas</div><div class="card"><dl class="kv">' +
       R.glossary.map(([k,v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") + '</dl></div>';
  h += '<div class="sec">Recuperación y vuelta al box</div><div class="card"><ul class="clean">' +
       R.recovery.map(l=>`<li>${esc(l)}</li>`).join("") + '</ul></div>';
  return h;
}

/* ---------- Exports ---------- */
function btwbText(w, id){
  const s = findSession(w ?? state.w, id ?? state.id);
  const L = [`${s.code} · ${s.dlabel} · ${s.title} (${s.total}')`];
  s.blocks.filter(b => b.type !== "cool").forEach(b => {
    L.push("", `${b.name} [${b.min}']`);
    b.items.forEach(i => {
      const real = i.n ? realStr(loadLog(logKey(s, i), i.n)) : "";
      const parts = [i.sets !== "—" ? i.sets.replace(/\s*×\s*/g, "×") : "", i.load, i.rir, i.tech, i.rest ? "rest " + i.rest : "", real ? "real: " + real : ""];
      L.push(`${i.code} ${i.ex}` + parts.filter(Boolean).map(x => " · " + x).join(""));
    });
  });
  return L.join("\n");
}
function csvAll(){
  const q = v => { v = String(v ?? ""); return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  const rows = [["codigo","fecha","ejercicio_codigo","ejercicio","prescrito","serie","kg","reps"]];
  P.forEach(w => w.sessions.forEach(s => s.blocks.forEach(b => b.items.forEach(i => {
    if(!i.n) return;
    const presc = [i.sets, i.load, i.rir].filter(Boolean).join(" · ");
    loadLog(logKey(s, i), i.n).forEach((st, ix) => {
      if(st.kg || st.reps) rows.push([s.code, s.date, i.code, i.ex, presc, ix + 1, st.kg, st.reps]);
    });
  }))));
  return rows.map(r => r.map(q).join(",")).join("\n") + "\n";
}
async function copyText(t, btn, okMsg){
  let ok = false;
  try{ await navigator.clipboard.writeText(t); ok = true; }
  catch(e){
    const ta = document.createElement("textarea");
    try{ ta.value = t; document.body.appendChild(ta); ta.select(); ok = document.execCommand("copy") === true; }catch(_){ ok = false; }
    ta.remove();
  }
  let m = $("#manual");
  if(ok){
    if(m) m.remove();
    btn.textContent = okMsg;
    setTimeout(() => { btn.textContent = btn.dataset.label; }, 1600);
  }else{
    // Sin portapapeles: se muestra el texto para copiarlo a mano.
    if(!m){ m = document.createElement("textarea"); m.id = "manual"; m.className = "manual"; m.readOnly = true; btn.after(m); }
    m.value = t;
    btn.textContent = "Copia manual: selecciona el texto";
  }
  return ok;
}

/* ---------- Render ---------- */
function render(){
  const app = $("#app");
  $("#back").hidden = state.view === "home";
  if(state.view === "home"){ $("#ttl").textContent = "Bridge Hipertrofia 2W"; $("#sub").textContent = "Nordic Wellness · ≤50'"; app.innerHTML = home(); }
  else if(state.view === "session"){ const s = findSession(state.w, state.id);
    $("#ttl").textContent = `${s.id} · ${s.title}`; $("#sub").textContent = `${s.code} · ${s.dlabel}`; app.innerHTML = session(); }
  else { $("#ttl").textContent = "Reglas"; $("#sub").textContent = "Bridge 2W"; app.innerHTML = rules(); }
  app.querySelectorAll(".tab").forEach(t => t.onclick = () => setWeek(+t.dataset.w));
  app.querySelectorAll(".day[data-id]").forEach(d => d.onclick = () => go("session", {id:d.dataset.id}));
  const r = $("#rules"); if(r) r.onclick = () => go("rules");
  const c = $("#copy"); if(c) c.onclick = () => copyText(btwbText(), c, "¡Copiado!");
  const x = $("#csv"); if(x) x.onclick = () => { const t = csvAll(), n = t.split("\n").length - 2;
    copyText(t, x, n ? `¡Copiado! ${n} series` : "Copiado (sin registros aún)"); };
}

function onField(e, final){
  const el = e.target;
  if(!el || !el.dataset || !el.dataset.k) return;
  const log = loadLog(el.dataset.k, +el.dataset.n), st = log[+el.dataset.i], f = el.dataset.f;
  st[f] = f === "kg" ? normKg(el.value) : normReps(el.value);
  saveLog(el.dataset.k);
  el.classList.toggle("has", !!st[f]);
  if(final) el.value = f === "kg" ? showKg(st.kg) : st.reps;   // normaliza lo escrito al salir del campo
}
$("#app").addEventListener("input", e => onField(e, false));
$("#app").addEventListener("change", e => onField(e, true));

render();

if("serviceWorker" in navigator){
  try{ navigator.serviceWorker.register("./sw.js", {scope:"./"}).catch(() => {}); }catch(e){}
}
</script>
</body>
</html>
"""

for a in ("__DATA__", "__RULES__", "__CAP__"):
    assert a in HTML and HTML.count(a) == 1, a
for a, b in (("__DATA__", DATA), ("__RULES__", RDATA), ("__CAP__", str(CAP))):
    assert a in HTML
    HTML = HTML.replace(a, b)

def write(name, text):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def read_bytes(name):
    with open(os.path.join(ROOT, name), "rb") as f:
        return f.read()

write(OUT, HTML)
write(INDEX, HTML)
write(SW, SW_JS)

# ---------------------------------------------------------------------------
# Validación sobre los ficheros escritos. Cualquier ✗ hace fallar el build.
# ---------------------------------------------------------------------------
results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("✓" if ok else "✗"), name, (f"— {detail}" if detail and not ok else ""))

def node_check(src_or_path, is_path=False):
    path = src_or_path
    tmp = None
    if not is_path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
        tmp.write(src_or_path); tmp.close(); path = tmp.name
    try:
        r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        return r.returncode == 0, (r.stderr or "").strip()[:400]
    finally:
        if tmp: os.unlink(tmp.name)

h = read_bytes(INDEX).decode("utf-8")
sw = read_bytes(SW).decode("utf-8")
check(f"{INDEX} idéntico byte a byte a {OUT}", read_bytes(INDEX) == read_bytes(OUT))

m = re.search(r"const P = (\[.*?\]);\n", h, re.S)
check("const P = [...];\\n parseable con la regex del repo", bool(m))
P2 = json.loads(m.group(1))
check("P leído del HTML == P del build", P2 == P)
sess = [(w, s) for w in P2 for s in w["sessions"]]
check("2 semanas × 6 sesiones = 12", len(P2) == 2 and all(len(w["sessions"]) == 6 for w in P2) and len(sess) == 12)
check(f"12 sesiones ≤ {CAP}' con todos los bloques",
      all(sum(b["min"] for b in s["blocks"]) == s["total"] <= CAP for _, s in sess))
check("Zona 2 solo en D6 (sábado)",
      all([s["id"] for s in w["sessions"] if any(b["type"] == "z2" for b in s["blocks"])] == ["D6"] for w in P2)
      and all(s["day"] == "Sábado" for _, s in sess if s["id"] == "D6"))
check("5 obligatorias + 1 opcional por semana",
      all(sum(1 for s in w["sessions"] if not s.get("optional")) == 5
          and [s["id"] for s in w["sessions"] if s.get("optional")] == ["D6"] for w in P2))
codes = [s["code"] for _, s in sess]
check("códigos BRG-S{1,2}-D{1..6} únicos",
      sorted(codes) == sorted(f"BRG-S{w}-D{d}" for w in (1, 2) for d in range(1, 7)) and len(set(codes)) == 12)
def date_ok(w, s):
    d = datetime.date.fromisoformat(s["date"])
    n = int(s["id"][1:])
    return (s["code"] == f"BRG-S{w['week']}-{s['id']}" and d.weekday() == n - 1 and DAYS[d.weekday()] == s["day"]
            and w["start"] <= s["date"] <= w["end"] and d == START + datetime.timedelta(days=(w["week"] - 1) * 7 + n - 1)
            and s["dfull"].endswith(d.strftime("%d/%m/%Y")) and s["dlabel"].endswith(d.strftime("%d/%m")))
check("códigos ↔ fechas ↔ día de la semana (S1 16–21/11, S2 23–28/11)",
      all(date_ok(w, s) for w, s in sess)
      and [s["date"] for _, s in sess] == [f"2026-11-{d}" for d in (16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28)])
check("nº de series derivado de `sets` en todos los ejercicios; D6 sin registro",
      all(i["n"] == n_sets(i["sets"]) for _, s in sess for b in s["blocks"] for i in b["items"])
      and all(i["n"] == 0 for _, s in sess if s["id"] == "D6" for b in s["blocks"] for i in b["items"])
      and all(any(i["n"] for b in s["blocks"] for i in b["items"]) for _, s in sess if s["id"] != "D6"))

scripts = re.findall(r"<script>(.*?)</script>", h, re.S)
check("un único <script> inline", len(scripts) == 1 and "<script src" not in h)
ok, err = node_check(scripts[0]); check("node --check JS del HTML", ok, err)
ok, err = node_check(os.path.join(ROOT, SW), True); check("node --check sw.js", ok, err)

check("sin URLs externas (http/https) en HTML ni sw.js",
      not re.search(r"https?:|[\"'(=]\s*//\w", h + sw, re.I))
check("sin referencias a la app principal", not any(f in (h + sw).lower() for f in FORBIDDEN))
check("router: navStack + replaceState solo en try/catch",
      "navStack.push" in h and h.count("history.") == 1 and "try{ history.replaceState" in h and "pushState" not in h)
lines = h.split("\n")
check("localStorage solo dentro de try (misma línea o las 2 anteriores)",
      all("try{" in "\n".join(lines[max(0, n - 2):n + 1]) for n, l in enumerate(lines) if "localStorage." in l)
      and sum("localStorage." in l for l in lines) >= 3)
check("service worker real: ./sw.js con scope ./, sin blob:",
      'register("./sw.js", {scope:"./"})' in h and "blob" not in h.lower() and "createObjectURL" not in h)
check(f"sw.js: caché {CACHE}; solo borra cachés {CACHE_PREFIX}*; nunca caches.match global",
      f'const CACHE = "{CACHE}";' in sw and sw.count("caches.delete") == 1
      and "keys.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k))" in sw
      and not re.search(r"(?<![\w.])caches\.match", sw))

if not os.path.isdir(os.path.join(ROOT, "node_modules", "jsdom")):
    check("jsdom instalado (ejecuta `npm install`)", False, "falta node_modules/jsdom")
else:
    r = subprocess.run(["node", "validate.mjs", INDEX, SW], cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.stderr.strip():
        sys.stdout.write(r.stderr)
    check("validate.mjs (jsdom normal + sandbox, exports, sw.js)", r.returncode == 0, f"exit {r.returncode}")

print()
for s in SESSIONS:
    print(f"  {s['id']} {s['title']:<22} {s['total']}'")
print("Tamaño:", round(len(h.encode('utf-8')) / 1024), "KB ·", OUT, "=", INDEX, "·", SW)
if not all(results):
    print(f"\nBUILD FALLIDO: {results.count(False)} validación(es) no pasan")
    sys.exit(1)
print(f"\nBUILD OK: {len(results)} validaciones del build + las de validate.mjs")
