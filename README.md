# Senthia Core — Automatización de publicaciones

Repositorio mínimo para publicar a diario en Instagram y Facebook a partir de
`plan.json`, usando GitHub Pages (hosting de imágenes) + GitHub Actions (publica
solo cada día).

## Contenido

- `plan.json` — calendario de 365 publicaciones (foto suelta o carrusel por día).
- `catalogo/imagenes/lavabo-01-*/render (n).jpg` — imágenes que se publican.
- `automatizacion/publish.py` — publicador (Graph API de Meta).
- `automatizacion/GUIA-AUTOMATIZACION.md` — **guía paso a paso desde cero**.
- `.github/workflows/publish-daily.yml` — tarea diaria automática.

## Puesta en marcha

Sigue `automatizacion/GUIA-AUTOMATIZACION.md`. En resumen:

1. **Settings → Pages**: Deploy from a branch → `main` / root.
2. Crear app de Meta y obtener token + IG_USER_ID + FB_PAGE_ID.
3. **Settings → Secrets and variables → Actions**: añadir
   `META_ACCESS_TOKEN`, `IG_USER_ID`, `FB_PAGE_ID`, `IMAGE_BASE_URL`.
4. **Actions → Run workflow** con `dry_run = true` para probar; luego en automático.

Las imágenes quedan públicas (es necesario para que Instagram pueda descargarlas).
Los tokens nunca van aquí: van en Secrets (nube) o en `.env` local (ignorado por git).
