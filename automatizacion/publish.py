# -*- coding: utf-8 -*-
"""
Senthia Core - Publicador diario en Instagram a partir de plan.json.

Usa la "Instagram API con inicio de sesion de Instagram" (graph.instagram.com).
Lee plan.json, elige la publicacion que toca (la mas antigua sin publicar con
fecha <= hoy), la sube a Instagram (foto suelta o carrusel), marca posted: true
y guarda plan.json.

Instagram exige que las imagenes esten en una URL publica: por eso se construye
la URL a partir de IMAGE_BASE_URL + la ruta relativa del plan (GitHub Pages).

Variables de entorno necesarias (ver .env.example):
  IG_ACCESS_TOKEN   Token de larga duracion de Instagram (panel de Meta -> Instagram
                    -> Configuracion de la API con inicio de sesion de Instagram)
  IG_USER_ID        ID de la cuenta de Instagram (numero)
  IMAGE_BASE_URL    Base publica de las imagenes (sin barra final),
                    p.ej. https://ujnapego.github.io/senthia-core
Opcionales:
  GRAPH_VERSION     Version de la API (def. v23.0)
  PLAN_PATH         Ruta a plan.json (def. ../plan.json relativo a este archivo)

Uso:
  python publish.py --dry-run          # no publica, solo muestra que haria
  python publish.py                    # publica la que toca hoy
  python publish.py --catch-up         # publica TODAS las atrasadas (una por una)
  python publish.py --date 2026-06-25  # finge que "hoy" es esa fecha
  python publish.py --post-id 42       # fuerza una publicacion concreta por id
"""
import os, sys, json, time, argparse, datetime as dt
from urllib.parse import quote

try:
    import requests
except ImportError:
    sys.exit("Falta la libreria 'requests'. Instala con: pip install -r requirements.txt")

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------- configuracion
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.instagram.com/{GRAPH_VERSION}"

def env(name, required=True, default=None):
    v = os.environ.get(name, default)
    if required and not v:
        sys.exit(f"ERROR: falta la variable de entorno {name}")
    return v

def log(msg):
    ts = dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ------------------------------------------------------------------- utilidades
def image_url(base, relpath):
    """Convierte 'catalogo/imagenes/lavabo-01-ciae/render (1).jpg' en URL publica."""
    segs = [quote(s) for s in relpath.split("/")]
    return base.rstrip("/") + "/" + "/".join(segs)

def full_caption(post):
    tags = " ".join(post.get("hashtags", []))
    cap = post.get("caption", "").strip()
    return (cap + "\n\n" + tags).strip() if tags else cap

def api_post(path, params):
    r = requests.post(f"{GRAPH}/{path}", data=params, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"API POST {path} -> {r.status_code}: {r.text}")
    return r.json()

def api_get(path, params):
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"API GET {path} -> {r.status_code}: {r.text}")
    return r.json()

# ---------------------------------------------------------------- Instagram API
def ig_wait_ready(creation_id, token, tries=20, delay=3):
    """Espera a que el contenedor este FINISHED antes de publicar."""
    for _ in range(tries):
        st = api_get(creation_id, {"fields": "status_code", "access_token": token})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Instagram: contenedor en ERROR -> {st}")
        time.sleep(delay)
    raise RuntimeError("Instagram: el contenedor no llego a FINISHED a tiempo")

def ig_publish(post, token, ig_user, base):
    urls = [image_url(base, p) for p in post["images"]]
    caption = full_caption(post)

    if post["type"] == "carousel":
        child_ids = []
        for u in urls:
            c = api_post(f"{ig_user}/media",
                         {"image_url": u, "is_carousel_item": "true", "access_token": token})
            child_ids.append(c["id"])
        parent = api_post(f"{ig_user}/media",
                          {"media_type": "CAROUSEL",
                           "children": ",".join(child_ids),
                           "caption": caption,
                           "access_token": token})
        creation_id = parent["id"]
    else:
        c = api_post(f"{ig_user}/media",
                     {"image_url": urls[0], "caption": caption, "access_token": token})
        creation_id = c["id"]

    ig_wait_ready(creation_id, token)
    res = api_post(f"{ig_user}/media_publish",
                   {"creation_id": creation_id, "access_token": token})
    return res.get("id")

# ------------------------------------------------------------------------- main
def load_plan(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_plan(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def pick_due(posts, today, post_id=None):
    if post_id is not None:
        return [p for p in posts if p["id"] == post_id]
    due = [p for p in posts if not p.get("posted") and p["date"] <= today]
    due.sort(key=lambda p: p["date"])
    return due

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--catch-up", action="store_true", help="publica todas las atrasadas")
    ap.add_argument("--date", help="fecha 'hoy' simulada YYYY-MM-DD")
    ap.add_argument("--post-id", type=int)
    args = ap.parse_args()

    plan_path = os.environ.get("PLAN_PATH") or os.path.join(HERE, "..", "plan.json")
    plan_path = os.path.abspath(plan_path)
    data = load_plan(plan_path)
    posts = data["posts"]

    today = args.date or dt.date.today().isoformat()
    due = pick_due(posts, today, args.post_id)
    if not due:
        log(f"No hay nada pendiente para hoy ({today}). Fin.")
        return
    # normalmente 2 publicaciones/dia (1 suelto + 1 carrusel); margen por si se
    # perdio un dia. Con --catch-up publica todas las atrasadas sin limite.
    if not args.catch_up and args.post_id is None:
        due = due[:4]

    log(f"Hoy={today}  a publicar={len(due)}  dry_run={args.dry_run}")

    if not args.dry_run:
        token   = env("IG_ACCESS_TOKEN")
        ig_user = env("IG_USER_ID")
        base    = env("IMAGE_BASE_URL")
    else:
        token = ig_user = None
        base = os.environ.get("IMAGE_BASE_URL", "https://ujnapego.github.io/senthia-core")

    published_any = False
    for post in due:
        head = f"#{post['id']} {post['date']} {post['type']} [{post['collection']}]"
        log(f"--- {head}")
        for u in post["images"]:
            log(f"      img: {image_url(base, u)}")
        log(f"      caption: {full_caption(post)[:120]}...")

        if args.dry_run:
            continue

        try:
            ig_id = ig_publish(post, token, ig_user, base)
        except Exception as e:
            log(f"      FALLO: {e}")
            post["last_error"] = str(e)
            save_plan(plan_path, data)
            sys.exit(1)

        post["posted"] = True
        post["posted_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        post["result"] = {"instagram_id": ig_id}
        post.pop("last_error", None)
        save_plan(plan_path, data)
        published_any = True
        log(f"      OK Instagram id={ig_id}  -> marcado posted:true")

    if args.dry_run:
        log("DRY-RUN: no se ha publicado ni modificado nada.")
    elif published_any:
        log("Hecho.")

if __name__ == "__main__":
    main()
