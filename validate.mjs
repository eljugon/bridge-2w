// Validación del PWA generado: jsdom (modo normal y sandbox), exports y sw.js.
// Uso: node validate.mjs [index.html] [sw.js]   — lo ejecuta build_bridge_2w.py.
import fs from "node:fs";
import vm from "node:vm";
import { JSDOM, VirtualConsole } from "jsdom";

const [htmlPath = "index.html", swPath = "sw.js"] = process.argv.slice(2);
const html = fs.readFileSync(htmlPath, "utf8");
const swSrc = fs.readFileSync(swPath, "utf8");
const ORIGIN = "https://eljugon.github.io";
const BASE = ORIGIN + "/bridge-2w/";
// Claves de la app principal (mismo origen): deben quedar intactas.
const FOREIGN = { "p12w-v18": '{"a":1}', "p12w-v18-logs-v1": '[{"x":"y"}]', "p16w-vita-outbox": "[]" };

let failed = 0, passed = 0;
function ok(name, cond, detail = "") {
  if (cond) { passed++; console.log("  ✓", name); }
  else { failed++; console.log("  ✗", name, detail ? "— " + detail : ""); }
}
const tick = () => new Promise(r => setTimeout(r, 0));

function open({ today = [2026, 11, 18], sandbox = false, quota = false, seed = {}, clipboard = true } = {}) {
  const errors = [], clip = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => errors.push(String(e && e.stack || e)));
  vc.on("error", e => errors.push(String(e)));
  const dom = new JSDOM(html, {
    url: BASE, runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(window) {
      const RealDate = window.Date;
      const fixed = new RealDate(today[0], today[1] - 1, today[2], 12, 0, 0).getTime();
      window.Date = class extends RealDate {
        constructor(...a) { if (a.length) super(...a); else super(fixed); }
        static now() { return fixed; }
      };
      window.scrollTo = () => {};
      for (const [k, v] of Object.entries(seed)) window.localStorage.setItem(k, v);
      if (clipboard) Object.defineProperty(window.navigator, "clipboard",
        { configurable: true, value: { writeText: async t => { clip.push(t); } } });
      if (sandbox) {
        const deny = () => { throw new window.DOMException("The operation is insecure.", "SecurityError"); };
        window.history.replaceState = deny;
        window.history.pushState = deny;
        Object.defineProperty(window, "localStorage", { configurable: true, get: deny });
      }
      if (quota) {
        const P = window.Storage.prototype;
        P.setItem = () => { throw new window.DOMException("quota", "QuotaExceededError"); };
      }
    },
  });
  const w = dom.window, d = w.document;
  return {
    dom, w, d, errors, clip,
    $: s => d.querySelector(s), $$: s => [...d.querySelectorAll(s)],
    state: () => w.eval("({...state})"),
    click: s => { const el = d.querySelector(s); if (!el) throw new Error("no existe " + s); el.click(); },
    type(el, v) {
      el.value = v;
      el.dispatchEvent(new w.Event("input", { bubbles: true }));
      el.dispatchEvent(new w.Event("change", { bubbles: true }));
    },
    dump() { const o = {}; for (let i = 0; i < w.localStorage.length; i++) { const k = w.localStorage.key(i); o[k] = w.localStorage.getItem(k); } return o; },
    close: () => w.close(),
  };
}

function parseCSV(t) {
  const rows = []; let row = [], cur = "", q = false;
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (q) { if (c === '"') { if (t[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
    else if (c === '"') q = true;
    else if (c === ",") { row.push(cur); cur = ""; }
    else if (c === "\n") { row.push(cur); rows.push(row); row = []; cur = ""; }
    else cur += c;
  }
  if (cur || row.length) { row.push(cur); rows.push(row); }
  return rows;
}

// ---------------------------------------------------------------- datos
const P = JSON.parse(html.match(/const P = (\[.*?\]);\n/s)[1]);
const sessions = P.flatMap(w => w.sessions.map(s => ({ w: w.week, s })));
const items = s => s.blocks.flatMap(b => b.items);
const totalSets = sessions.reduce((a, { s }) => a + items(s).reduce((x, i) => x + i.n, 0), 0);

// ---------------------------------------------------------------- navegación
async function navFlow(label, opts) {
  console.log(`jsdom · ${label}`);
  const a = open(opts);
  try {
    ok("carga sin errores y portada con 6 sesiones", a.errors.length === 0 && a.$$(".day[data-id]").length === 6, a.errors[0]);
    ok("portada: S1 por defecto y D3 (mié 18/11) destacada como hoy",
      a.state().w === 1 && a.$$(".card.today").length === 1 && a.$(".card.today .day").dataset.id === "D3");
    ok("portada: cada sesión muestra código y fecha",
      a.$$(".day[data-id] .cd").map(e => e.textContent).join("|") ===
      P[0].sessions.map(s => `${s.code} · ${s.dlabel}`).join("|"));
    a.click('.day[data-id="D3"]');
    ok("portada → sesión D3: cabecera con BRG-S1-D3 y fecha",
      a.state().view === "session" && a.$("#scode").textContent === "BRG-S1-D3 · Miércoles 18/11/2026"
      && a.$("#sub").textContent.startsWith("BRG-S1-D3") && !a.$("#back").hidden);
    a.click('.tab[data-w="2"]');
    ok("cambio de semana en la sesión → BRG-S2-D3 (25/11)",
      a.state().w === 2 && a.state().id === "D3" && a.$("#scode").textContent === "BRG-S2-D3 · Miércoles 25/11/2026");
    if (!opts.sandbox) ok("URL sincronizada con replaceState", a.w.location.hash === "#session-D3-w2", a.w.location.hash);
    else ok("History API lanza SecurityError y la URL no cambia", a.w.location.hash === "");
    a.click("#back");
    ok("atrás → portada (conserva la semana 2), botón atrás oculto",
      a.state().view === "home" && a.state().w === 2 && a.$("#back").hidden && a.$$(".day[data-id]").length === 6);
    a.click("#back");
    ok("atrás con navStack vacío no hace nada", a.state().view === "home");
    a.click("#rules");
    ok("portada → reglas → atrás", a.state().view === "rules" && a.$$(".card.wk").length === 2 && (a.click("#back"), a.state().view === "home"));

    // registro en memoria / almacenamiento
    a.click('.tab[data-w="1"]'); a.click('.day[data-id="D2"]');
    const kg = a.$('input[data-k="BRG-S1-D2:A1"][data-i="0"][data-f="kg"]');
    const reps = a.$('input[data-k="BRG-S1-D2:A1"][data-i="0"][data-f="reps"]');
    ok("inputs: kg type=text inputmode=decimal · reps inputmode=numeric",
      kg.type === "text" && kg.getAttribute("inputmode") === "decimal" && reps.type === "text" && reps.getAttribute("inputmode") === "numeric");
    a.type(kg, " 92,5 "); a.type(reps, "8");
    ok('"92,5" se acepta y se normaliza', kg.value === "92,5" && a.w.eval('mem["BRG-S1-D2:A1"][0].kg') === "92.5");
    ok("BTWB incluye lo registrado", a.w.btwbText(1, "D2").includes("A1 Bench Press · 4×6–8 · 92,5 kg (74 %) · RIR 2 · rest 75\" · real: 92,5×8"));
    const persists = !opts.sandbox && !opts.quota;
    ok(persists ? "aviso de almacenamiento oculto" : "aviso visible: sin almacenamiento, la app sigue funcionando",
      a.$("#warn").hidden === persists);
    a.click("#copy"); await tick();
    ok("botón Copiar para BTWB: primera línea con el código", a.clip.at(-1).split("\n")[0] === "BRG-S1-D2 · mar 17/11 · Upper A (50')", a.clip.at(-1));
    a.click("#back"); a.click("#csv"); await tick();
    ok("botón Exportar todo: CSV con la serie registrada",
      a.clip.at(-1) === 'codigo,fecha,ejercicio_codigo,ejercicio,prescrito,serie,kg,reps\nBRG-S1-D2,2026-11-17,A1,Bench Press,"4 × 6–8 · 92,5 kg (74 %) · RIR 2",1,92.5,8\n', a.clip.at(-1));
    ok("sin errores de ejecución durante el flujo", a.errors.length === 0, a.errors[0]);
    return a;
  } catch (e) { ok("flujo sin excepciones", false, e.stack); return a; }
}

const normal = await navFlow("modo normal", { seed: FOREIGN });
console.log("jsdom · persistencia (modo normal)");
{
  const dump = normal.dump();
  ok('localStorage: clave "BRG-S1-D2:A1" con lo registrado',
    dump["BRG-S1-D2:A1"] === '[{"kg":"92.5","reps":"8"},{"kg":"","reps":""},{"kg":"","reps":""},{"kg":"","reps":""}]', dump["BRG-S1-D2:A1"]);
  ok("claves de la app principal intactas y ninguna clave ajena al prefijo BRG-",
    Object.entries(FOREIGN).every(([k, v]) => dump[k] === v)
    && Object.keys(dump).filter(k => !(k in FOREIGN)).every(k => /^BRG-S[12]-D[1-5]:[A-Z][0-9+]?$/.test(k)), Object.keys(dump).join(","));
  normal.close();
  const b = open({ seed: dump });
  b.click('.day[data-id="D2"]');
  ok("recarga: el registro persiste en los campos",
    b.$('input[data-k="BRG-S1-D2:A1"][data-i="0"][data-f="kg"]').value === "92,5"
    && b.$('input[data-k="BRG-S1-D2:A1"][data-i="0"][data-f="reps"]').value === "8"
    && b.$('input[data-k="BRG-S1-D2:A1"][data-i="1"][data-f="kg"]').value === "");
  b.type(b.$('input[data-k="BRG-S1-D2:A1"][data-i="0"][data-f="kg"]'), "");
  b.type(b.$('input[data-k="BRG-S1-D2:A1"][data-i="0"][data-f="reps"]'), "");
  ok("vaciar el registro elimina la clave", !("BRG-S1-D2:A1" in b.dump()) && Object.entries(FOREIGN).every(([k, v]) => b.dump()[k] === v));
  b.close();
}
(await navFlow("modo sandbox (History API y localStorage lanzan SecurityError)", { sandbox: true })).close();
(await navFlow("localStorage.setItem lanza QuotaExceededError", { quota: true })).close();

console.log("jsdom · portapapeles no disponible");
{
  const a = open({ clipboard: false });
  a.click('.day[data-id="D1"]'); a.click("#copy"); await tick();
  ok("sin portapapeles: muestra el texto para copiarlo a mano",
    a.$("#manual") && a.$("#manual").value === a.w.btwbText(1, "D1") && a.errors.length === 0, a.errors[0]);
  a.close();
}

// ---------------------------------------------------------------- fechas
console.log("jsdom · semana por defecto y sesión de hoy");
for (const [today, w, id] of [
  [[2026, 11, 15], 1, null], [[2026, 11, 16], 1, "D1"], [[2026, 11, 21], 1, "D6"], [[2026, 11, 22], 1, null],
  [[2026, 11, 23], 2, "D1"], [[2026, 11, 28], 2, "D6"], [[2026, 11, 29], 2, null], [[2026, 12, 5], 2, null], [[2026, 10, 1], 1, null],
]) {
  const a = open({ today });
  const t = a.$$(".card.today .day").map(e => e.dataset.id);
  ok(`${today.join("-")} → S${w}, hoy = ${id ?? "ninguna"}`,
    a.state().w === w && (id ? t.length === 1 && t[0] === id : t.length === 0) && a.errors.length === 0);
  if (id) { a.click(`.tab[data-w="${w === 1 ? 2 : 1}"]`); ok("  la otra semana no destaca ninguna sesión", a.$$(".card.today").length === 0); }
  a.close();
}

// ---------------------------------------------------------------- exports en las 12 sesiones
console.log("exports · 12 sesiones");
{
  const a = open();
  let good = true, why = "";
  for (const { w, s } of sessions) {
    const t = a.w.btwbText(w, s.id), L = t.split("\n");
    const ex = items(s).filter(i => !s.blocks.find(b => b.type === "cool" && b.items.includes(i)));
    if (!L[0].startsWith(s.code + " · ") || t.includes("real:") || t.includes("undefined")
      || !ex.every(i => L.some(l => l.startsWith(`${i.code} ${i.ex}`)))) { good = false; why = s.code; }
  }
  ok("BTWB sin datos: 12 textos, código en la primera línea, todos los ejercicios, sin «real:»", good, why);
  const csv0 = a.w.csvAll();
  ok("CSV sin datos: solo cabecera", csv0 === "codigo,fecha,ejercicio_codigo,ejercicio,prescrito,serie,kg,reps\n");

  // UI: nº de campos por sesión y D6 sin registro
  good = true; why = "";
  for (const { w, s } of sessions) {
    a.w.eval(`state = {view:"home", w:${w}, id:null}; navStack.length = 0; render()`);
    a.click(`.day[data-id="${s.id}"]`);
    const n = items(s).reduce((x, i) => x + i.n, 0), inputs = a.$$("#app input");
    if (inputs.length !== 2 * n || (s.id === "D6" && inputs.length !== 0) || !a.$("#scode").textContent.startsWith(s.code)) { good = false; why = `${s.code}: ${inputs.length} campos, esperados ${2 * n}`; }
    for (const i of items(s)) if (a.$$(`input[data-k="${s.code}:${i.code}"]`).length !== 2 * i.n) { good = false; why = `${s.code}:${i.code}`; }
  }
  ok(`sesión: un campo de kg y otro de reps por serie (${totalSets} series en total); D6 sin campos`, good, why);
  a.close();

  // con datos en todas las series
  const seed = { ...FOREIGN };
  for (const { s } of sessions) for (const i of items(s)) if (i.n)
    seed[`${s.code}:${i.code}`] = JSON.stringify(Array.from({ length: i.n }, (_, k) => ({ kg: String(40 + k * 2.5), reps: String(12 - k) })));
  const b = open({ seed });
  good = true; why = "";
  for (const { w, s } of sessions) {
    const L = b.w.btwbText(w, s.id).split("\n");
    for (const i of items(s)) {
      const line = L.find(l => l.startsWith(`${i.code} ${i.ex}`));
      const exp = "real: " + Array.from({ length: i.n }, (_, k) => `${String(40 + k * 2.5).replace(".", ",")}×${12 - k}`).join(", ");
      if (i.n && !(line && line.endsWith(" · " + exp))) { good = false; why = `${s.code}:${i.code} → ${line}`; }
      if (!i.n && line && line.includes("real:")) { good = false; why = `${s.code}:${i.code}`; }
    }
  }
  ok("BTWB con datos: 12 textos con «real: kg×reps» en cada ejercicio con series", good, why);
  const rows = parseCSV(b.w.csvAll());
  const codeDate = Object.fromEntries(sessions.map(({ s }) => [s.code, s.date]));
  ok(`CSV con datos: cabecera + ${totalSets} filas de 8 columnas, código ↔ fecha coherentes`,
    rows.length === totalSets + 1 && rows.every(r => r.length === 8)
    && rows.slice(1).every(r => codeDate[r[0]] === r[1] && /^\d+(\.\d+)?$/.test(r[6]) && /^\d+$/.test(r[7]) && !r[0].endsWith("D6"))
    && new Set(rows.slice(1).map(r => `${r[0]}:${r[2]}:${r[5]}`)).size === totalSets, `filas: ${rows.length - 1}`);
  ok("exportar no altera las claves de la app principal", Object.entries(FOREIGN).every(([k, v]) => b.dump()[k] === v) && b.errors.length === 0);
  b.close();

  // registro parcial y datos corruptos
  const c = open({ seed: { "BRG-S1-D1:A": '[{"kg":"110","reps":""},{},{"kg":"","reps":"6"}]', "BRG-S1-D1:B": "{no es json", "BRG-S1-D1:D": '"x"' } });
  const t = c.w.btwbText(1, "D1");
  ok("registro parcial («110×?, –, ?×6») y JSON corrupto tolerados",
    t.includes("real: 110×?, –, ?×6") && t.split("real:").length === 2 && c.errors.length === 0, t);
  c.close();
}

// ---------------------------------------------------------------- sw.js
console.log("sw.js · ejecución simulada");
{
  const store = new Map([["p12w-v18", new Map()], ["otra-app-v3", new Map()], ["bridge2w-v0", new Map()], ["bridge2w-old", new Map()]]);
  const opened = [], deleted = [], fetched = [], handlers = {};
  const mkCache = m => ({
    addAll: async l => { l.forEach(u => m.set(new URL(u, BASE).href, "shell")); },
    put: async (req, res) => { m.set(req.url, res); },
    match: async req => m.get(typeof req === "string" ? new URL(req, BASE).href : req.url),
  });
  const caches = {
    open: async n => { opened.push(n); if (!store.has(n)) store.set(n, new Map()); return mkCache(store.get(n)); },
    keys: async () => [...store.keys()],
    delete: async n => { deleted.push(n); return store.delete(n); },
    match: async () => { throw new Error("caches.match global no permitido"); },
  };
  const self = {
    addEventListener: (t, f) => { handlers[t] = f; }, skipWaiting: async () => {}, clients: { claim: async () => {} },
    registration: { scope: BASE }, location: new URL(BASE + "sw.js"),
  };
  const fetch = async req => { fetched.push(req.url); return { ok: true, clone() { return "copia"; } }; };
  vm.runInNewContext(swSrc, { self, caches, fetch, URL, Promise, Response: { error: () => "error" } });
  const fire = async (type, extra = {}) => { const waits = []; let resp; handlers[type]({ waitUntil: p => waits.push(p), respondWith: p => { resp = p; }, ...extra });
    await Promise.all(waits); return resp; };
  await fire("install");
  await fire("activate");
  ok("activate borra solo cachés bridge2w-* antiguas", deleted.sort().join() === "bridge2w-old,bridge2w-v0" && store.has("p12w-v18") && store.has("otra-app-v3") && store.has("bridge2w-v1"), deleted.join());
  ok("install precachea ./ e index.html en bridge2w-v1", store.get("bridge2w-v1").has(BASE) && store.get("bridge2w-v1").has(BASE + "index.html"));
  const out = [
    await fire("fetch", { request: { method: "GET", url: ORIGIN + "/otra-app/index.html" } }),
    await fire("fetch", { request: { method: "GET", url: ORIGIN + "/" } }),
    await fire("fetch", { request: { method: "POST", url: BASE } }),
  ];
  ok("fetch: ignora peticiones fuera de /bridge-2w/ y las que no son GET", out.every(r => r === undefined) && fetched.length === 0);
  const hit = await fire("fetch", { request: { method: "GET", url: BASE } });
  ok("fetch dentro del alcance: responde desde la caché propia y la refresca", (await hit) === "shell" && fetched.join() === BASE);
  ok("solo abre la caché bridge2w-v1", opened.every(n => n === "bridge2w-v1"));
}

console.log(`\nvalidate.mjs: ${passed} OK, ${failed} fallos`);
process.exit(failed ? 1 : 0);
