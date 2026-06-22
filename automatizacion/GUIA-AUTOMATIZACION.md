# Automatización de publicaciones — Senthia Core (Instagram + Facebook)

Guía **paso a paso desde cero**. Al terminar, cada día a una hora fija se publicará
sola la imagen (o el carrusel) que toca según `plan.json`, en Instagram y Facebook,
y se marcará `posted: true`.

---

## 0. Cómo funciona (resumen)

```
plan.json  ──►  GitHub Actions (cada día a las 10:00)  ──►  Graph API de Meta  ──►  Instagram + Facebook
   ▲                         │
   └──── imágenes servidas por GitHub Pages (URL pública) ◄── Meta descarga la imagen desde esa URL
```

- **GitHub Pages**: aloja tus imágenes en una URL pública (Instagram lo exige).
- **GitHub Actions**: el "robot" que se ejecuta solo cada día (no necesita tu PC encendido).
- **Graph API de Meta**: la vía oficial para publicar en IG/FB.

Piezas que ya te he dejado hechas en el proyecto:
- `automatizacion/publish.py` — el publicador.
- `automatizacion/requirements.txt` — dependencias.
- `automatizacion/.env.example` — plantilla de configuración.
- `.github/workflows/publish-daily.yml` — la tarea diaria automática.
- `.gitignore` — para no subir nunca tus tokens.

Solo tienes que hacer la configuración de cuentas (una vez) que se explica abajo.

---

## 1. Requisitos previos (cuentas)

1. **Instagram en modo Business o Creator.**
   App de Instagram → Configuración → Cuenta → "Cambiar a cuenta profesional".
2. **Una página de Facebook** (no un perfil personal) de Senthia Core.
3. **Vincular Instagram con esa página de Facebook.**
   En la página de Facebook → Configuración → Cuentas vinculadas → Instagram → conectar.
4. Una cuenta de **GitHub** (gratis): https://github.com/signup

> Importante: con esto basta. **No necesitas "App Review" de Meta** porque vas a
> publicar solo en TUS propias cuentas y tú eres el administrador. La app puede
> quedarse en modo *Development*.

---

## 2. Subir el proyecto a GitHub

1. Crea un repositorio nuevo en https://github.com/new
   - Nombre sugerido: `senthia-core` (sin espacios ni acentos).
   - Público (necesario para que GitHub Pages sirva las imágenes gratis).
2. Sube el proyecto. Desde la carpeta del proyecto, en una terminal:

   ```bash
   git add .
   git commit -m "Web + catálogo + automatización"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/senthia-core.git
   git push -u origin main
   ```

   (Si Git te pide identificarte, usa tu usuario de GitHub y un *Personal Access Token*
   como contraseña: GitHub → Settings → Developer settings → Personal access tokens.)

---

## 3. Activar GitHub Pages (hosting de las imágenes)

1. En el repo: **Settings → Pages**.
2. En "Build and deployment" → Source: **Deploy from a branch**.
3. Branch: **main**, carpeta **/ (root)**. Guarda.
4. Espera 1-2 minutos. Tu sitio quedará en:

   ```
   https://TU_USUARIO.github.io/senthia-core/
   ```

5. Comprueba que una imagen carga. Abre en el navegador (ojo a `%20` por los espacios):

   ```
   https://TU_USUARIO.github.io/senthia-core/catalogo/imagenes/lavabo-01-ciae/render%20(1).jpg
   ```

   Si ves la foto, el hosting está listo. **Esa base** (`https://TU_USUARIO.github.io/senthia-core`)
   es tu `IMAGE_BASE_URL`.

---

## 4. Crear la app de Meta y conectar IG + FB

1. Entra en https://developers.facebook.com/ → "Mis Apps" → **Crear app**.
2. Tipo de app: **Business**. Pon un nombre (p.ej. "Senthia Publicador").
3. Dentro de la app, añade los productos:
   - **Instagram Graph API**
   - **Facebook Login** (lo usaremos solo para generar el token).
4. En **App settings → Basic** anota el **App ID** y el **App Secret** (los necesitarás).

---

## 5. Conseguir los IDs (IG_USER_ID y FB_PAGE_ID)

Usa el **Explorador de la Graph API**:
https://developers.facebook.com/tools/explorer/

1. Arriba a la derecha, selecciona tu app.
2. "User or Page": deja **User token**.
3. Pulsa **Add a permission** y marca estos permisos:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `instagram_basic`
   - `instagram_content_publish`
   - `business_management`
4. Pulsa **Generate Access Token** y acepta. Guarda ese token (es de corta duración, lo cambiaremos luego).
5. Consulta tu página y su Instagram. En la barra de consulta escribe y ejecuta:

   ```
   me/accounts?fields=name,id,instagram_business_account
   ```

   - El `id` de tu página = **FB_PAGE_ID**.
   - El `instagram_business_account.id` = **IG_USER_ID**.

   Si `instagram_business_account` no aparece, revisa el paso 1.3 (vincular IG con la página).

---

## 6. Generar el token de larga duración (recomendado: que no caduque)

El token del paso 5 caduca en ~1 hora. Necesitas uno duradero. Dos opciones:

### Opción A — Token de página de larga duración (rápida)

1. Cambia el token corto por uno largo (pega en el navegador, sustituyendo valores):

   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=TOKEN_CORTO
   ```

   Te devuelve un `access_token` de usuario de ~60 días.

2. Con ese token largo, pide el **token de página** (este suele ser no caducable):

   ```
   https://graph.facebook.com/v21.0/me/accounts?access_token=TOKEN_LARGO_DE_USUARIO
   ```

   Copia el `access_token` de tu página. **Ese es tu `META_ACCESS_TOKEN`.**

### Opción B — System User (recomendada, "pon y olvida")

1. https://business.facebook.com/ → **Configuración del negocio → Usuarios → Usuarios del sistema**.
2. Crea un usuario del sistema (rol Admin).
3. **Asignar activos**: añade tu **página** de Facebook con control total.
4. **Generar nuevo token**: elige la app, **caducidad: Nunca**, y marca los permisos
   `pages_manage_posts`, `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`.
5. Copia el token. **Ese es tu `META_ACCESS_TOKEN`** y no caduca.

> Comprueba un token cuando quieras en: https://developers.facebook.com/tools/debug/accesstoken/

---

## 7. Configurar los Secrets en GitHub

En el repo: **Settings → Secrets and variables → Actions → New repository secret**.
Crea estos 4 secretos:

| Nombre              | Valor                                                        |
|---------------------|-------------------------------------------------------------|
| `META_ACCESS_TOKEN` | el token del paso 6                                         |
| `IG_USER_ID`        | el `instagram_business_account.id` del paso 5              |
| `FB_PAGE_ID`        | el `id` de la página del paso 5                            |
| `IMAGE_BASE_URL`    | `https://TU_USUARIO.github.io/senthia-core` (paso 3, sin `/` final) |

> Los secretos están cifrados; nadie (ni tú) puede volver a leerlos, solo reemplazarlos.

---

## 8. Probar sin publicar (dry-run)

1. En el repo: pestaña **Actions** → "Publicacion diaria Senthia Core" → **Run workflow**.
2. En `dry_run` pon **true** y ejecuta.
3. Abre el run y mira el log: debe listar la publicación que tocaría, las URLs de
   imagen y el texto. No publica nada.
4. **Verifica** que las URLs de imagen del log abren bien en el navegador.

---

## 9. Primera publicación real (manual)

1. **Actions → Run workflow** con `dry_run` = **false**.
   - Por defecto publica solo **la más antigua pendiente** (una).
2. Revisa Instagram y Facebook: debe aparecer el post.
3. Vuelve al repo: `plan.json` tendrá esa entrada con `posted: true`, `posted_at`
   y los IDs devueltos (commit automático del bot).

> ¿Vas con varios días de retraso y quieres ponerte al día de golpe? Ejecuta con
> `catch_up` = **true** (publica todas las atrasadas, una tras otra).

---

## 10. Dejarlo en automático

¡Ya está! El workflow tiene programado:

```
cron: "0 8 * * *"   →   08:00 UTC = 10:00 (verano) / 09:00 (invierno) en España
```

A partir de ahora se ejecuta solo cada día y publica la del día.

**Cambiar la hora:** edita `.github/workflows/publish-daily.yml`, línea del `cron`
(en UTC). Ej. para las 19:00 de verano en España → `0 17 * * *`.

---

## 11. Mantenimiento

- **Token caducado** (si usaste la Opción A): la publicación fallará con un error de
  token. Repite el paso 6 y actualiza el secreto `META_ACCESS_TOKEN`. Con la Opción B
  (System User, "Nunca") no hace falta.
- **Si un día falla**: el run queda en rojo en Actions y el post NO se marca como
  publicado, así que el día siguiente lo reintenta (queda pendiente). El error se
  guarda en `last_error` dentro de ese post en `plan.json`.
- **Añadir/editar publicaciones**: regenera `plan.json` con
  `python catalogo/_build/build_plan.py` y haz `git push`. (Respeta `posted: true`
  de las ya publicadas si editas a mano; el regenerador crea un plan nuevo desde cero,
  úsalo antes de empezar a publicar.)
- **Pausar la automatización**: Actions → el workflow → "•••" → **Disable workflow**.

---

## 12. Probar en tu PC (opcional)

Si quieres probar en local antes de subir nada:

```bash
cd automatizacion
copy .env.example .env        # y rellena .env con tus valores reales
pip install -r requirements.txt

# Probar sin publicar:
python publish.py --dry-run --catch-up

# Publicar de verdad la que toque hoy:
python publish.py
```

(En PowerShell, para cargar `.env` puedes usar variables de entorno manualmente o
ejecutar dentro de un entorno que las lea; en GitHub Actions esto ya está resuelto.)

---

## Notas técnicas

- **Formato de imagen**: Instagram admite JPG en relación de aspecto entre 4:5 y
  1.91:1. Algún render muy panorámico podría recortarse en el feed. Si te importa,
  evita usar esos encuadres extra-anchos como foto suelta.
- **Límites**: la API permite hasta 25 publicaciones de IG cada 24 h. Aquí usamos 1/día.
- **Privacidad**: el repo es público para que GitHub Pages sirva las imágenes. Si no
  quieres que el catálogo sea público, dímelo y montamos hosting alternativo (Cloudinary,
  un bucket, o tu propio dominio).
- **Seguridad**: nunca pongas el token en el código ni en `plan.json`. Va siempre en
  Secrets (nube) o en `.env` (local, ignorado por git).
```
