# bridge-2w

PWA del **Bridge Hipertrofia 2W**: 2 semanas (lun 16/11/2026 – dom 29/11/2026) en Nordic
Wellness, con un tope de 50' por sesión. Repo dedicado en exclusiva a este bridge; se
archivará cuando termine.

App: <https://eljugon.github.io/bridge-2w/> (GitHub Pages desde `main` / root).

## Abrir e instalar en el iPhone

1. Abre <https://eljugon.github.io/bridge-2w/> en **Safari** (no en otro navegador ni
   dentro de otra app).
2. Pulsa **Compartir** → **Añadir a pantalla de inicio** → **Añadir**.
3. Abre la app desde el icono una vez con conexión. A partir de ahí funciona sin red.

La portada abre en la semana en curso y destaca la sesión de hoy. En cada sesión hay un
campo de kg y otro de reps por serie; se guardan solos en el dispositivo.

- **Copiar para BTWB** (en cada sesión): texto de la sesión con lo registrado.
- **Exportar todo (CSV)** (en la portada): registro completo de las 2 semanas, con
  columnas `codigo,fecha,ejercicio_codigo,ejercicio,prescrito,serie,kg,reps` (kg con punto
  decimal).

El registro vive **solo en ese dispositivo y en esa instalación**: la app de la pantalla
de inicio y Safari pueden no compartir datos. Registra siempre desde el mismo sitio.

## Al terminar el bridge

1. **Antes de borrar nada: Exportar todo (CSV)** y pega el resultado en Notas o en un
   correo. Borrar la app o los datos del sitio elimina el registro sin vuelta atrás.
2. Borra la app de la pantalla de inicio (mantén pulsado el icono → Eliminar app).
3. Datos del sitio: no los borres desde Ajustes → Safari → Avanzado → Datos de sitios
   web, porque `eljugon.github.io` es un único sitio para iOS y se llevaría también los
   datos de las demás apps publicadas en ese dominio. Borrar la app de la pantalla de
   inicio ya elimina sus datos. Si además lo usaste en Safari, abre la URL en Safari una
   última vez y ejecuta el limpiador de abajo.
4. Archiva el repo: Settings → General → Danger Zone → **Archive this repository**
   (y, si quieres retirar la URL, desactiva antes Pages en Settings → Pages).

Limpiador (solo toca lo de este bridge: claves `BRG-…`, caché `bridge2w-…` y su service
worker). Pégalo en la consola web con la app abierta, o guárdalo como marcador
anteponiendo `javascript:`:

```js
(async()=>{Object.keys(localStorage).filter(k=>k.startsWith("BRG-")).forEach(k=>localStorage.removeItem(k));for(const k of await caches.keys())if(k.startsWith("bridge2w-"))await caches.delete(k);for(const r of await navigator.serviceWorker.getRegistrations())if(r.scope.endsWith("/bridge-2w/"))await r.unregister();alert("Bridge 2W: datos borrados")})()
```

## Qué guarda y dónde

GitHub Pages sirve todos los repos del usuario desde el mismo origen, así que
`localStorage` y Cache Storage se comparten con cualquier otra app publicada ahí. Esta
app solo usa:

| Recurso | Nombre |
| --- | --- |
| `localStorage` | una clave por ejercicio: `BRG-S{semana}-D{día}:{ejercicio}`, p. ej. `BRG-S1-D3:A1` |
| Cache Storage | `bridge2w-v1` |
| Service worker | `sw.js`, alcance `/bridge-2w/` |

Al activarse, el service worker solo borra cachés cuyo nombre empieza por `bridge2w-`.
Sin backend ni dependencias externas en tiempo de ejecución (tampoco fuentes).

## Estructura

| Archivo | |
| --- | --- |
| `build_bridge_2w.py` | generador: datos del programa, validaciones, escribe los outputs |
| `bridge_hipertrofia_2w_v1.html` | output versionado |
| `index.html` | copia idéntica del último output (URL estable) |
| `sw.js` | service worker, generado por el build |
| `validate.mjs` | pruebas con jsdom que ejecuta el build |
| `package.json` | jsdom como única devDependency |

## Build

```sh
npm install                  # solo la primera vez (jsdom)
python3 build_bridge_2w.py
```

El build escribe los tres outputs y falla (código 1) si no pasa alguna validación:
≤ 50' en las 12 sesiones, Zona 2 solo el sábado, códigos `BRG-S{1,2}-D{1..6}` coherentes
con fecha y día, `node --check` del JS, navegación y registro en jsdom (modo normal y
sandbox), exports BTWB/CSV en las 12 sesiones, `sw.js` simulado y ausencia de URLs
externas.

No edites a mano `index.html`, `bridge_hipertrofia_2w_v1.html` ni `sw.js`: cambia el
generador y vuelve a ejecutarlo. Si cambia el output publicado, sube `VERSION` en el
generador (nuevo `_v{N}.html` y nueva caché `bridge2w-v{N}`).
