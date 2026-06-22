# -*- coding: utf-8 -*-
"""
Senthia Core - Refresco automatico del token de larga duracion de Instagram.

El token de Instagram caduca a los 60 dias. Este script lo refresca (lo renueva
por otros 60 dias) y guarda el token nuevo en el Secret de GitHub IG_ACCESS_TOKEN,
para que la publicacion diaria nunca se quede sin token. Pensado para ejecutarse
una vez por semana desde GitHub Actions.

Variables de entorno:
  IG_ACCESS_TOKEN   token actual de Instagram (Secret del repo)
  GH_PAT            Personal Access Token con permiso 'Secrets: Read and write'
  GH_REPO           "owner/repo" (lo pasa Actions con github.repository)

Requisitos: requests, pynacl
"""
import os, sys, base64
import requests
from nacl import encoding, public

IG_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
GH_PAT   = os.environ.get("GH_PAT")
REPO     = os.environ.get("GH_REPO", "ujnapego/senthia-core")
SECRET   = "IG_ACCESS_TOKEN"

if not IG_TOKEN or not GH_PAT:
    sys.exit("ERROR: faltan IG_ACCESS_TOKEN o GH_PAT")

# 1) Refrescar el token de Instagram -----------------------------------------
r = requests.get("https://graph.instagram.com/refresh_access_token",
                 params={"grant_type": "ig_refresh_token", "access_token": IG_TOKEN},
                 timeout=60)
if r.status_code >= 400:
    sys.exit(f"ERROR al refrescar el token de Instagram: {r.status_code} {r.text}")
data = r.json()
new_token = data.get("access_token")
expires_in = int(data.get("expires_in", 0))
if not new_token:
    sys.exit(f"ERROR: respuesta sin access_token -> {data}")
print(f"Token de Instagram refrescado. Vuelve a caducar en ~{expires_in // 86400} dias.")

# 2) Guardar el token nuevo en el Secret de GitHub ---------------------------
H = {"Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json"}
base = f"https://api.github.com/repos/{REPO}/actions/secrets"

pk = requests.get(f"{base}/public-key", headers=H, timeout=30)
if pk.status_code >= 400:
    sys.exit(f"ERROR leyendo public-key (revisa el permiso del GH_PAT): {pk.status_code} {pk.text}")
pk = pk.json()

sealed = public.SealedBox(public.PublicKey(pk["key"].encode(), encoding.Base64Encoder()))
enc = base64.b64encode(sealed.encrypt(new_token.encode())).decode()

put = requests.put(f"{base}/{SECRET}", headers=H, timeout=30,
                   json={"encrypted_value": enc, "key_id": pk["key_id"]})
if put.status_code >= 400:
    sys.exit(f"ERROR actualizando el Secret {SECRET}: {put.status_code} {put.text}")
print(f"Secret {SECRET} actualizado correctamente (HTTP {put.status_code}).")
