#!/usr/bin/env bash
set -euo pipefail

# Elimina TODO en CRI-O: contenedores, pods y (opcional) imágenes
# Usa el socket de CRI-O y crictl

# Preferir sudo no interactivo; fallback a interactivo
if sudo -n true >/dev/null 2>&1; then
  SUDO="sudo -n"
else
  SUDO="sudo"
fi

START_EPOCH=$(date +%s)
log() { printf "[%s +%ss] %s\n" "$(date +%H:%M:%S)" "$(( $(date +%s) - START_EPOCH ))" "$*"; }
STOP_TIMEOUT=${STOP_TIMEOUT:-120}

command -v crictl >/dev/null 2>&1 || { echo "crictl no encontrado" >&2; exit 1; }

# Apuntar crictl a CRI-O si no está configurado
export CONTAINER_RUNTIME_ENDPOINT="${CONTAINER_RUNTIME_ENDPOINT:-unix:///var/run/crio/crio.sock}"

log "[nuke] Usando CONTAINER_RUNTIME_ENDPOINT=$CONTAINER_RUNTIME_ENDPOINT"

# 1) Parar todos los contenedores
log "[nuke] Parando contenedores en ejecución (timeout ${STOP_TIMEOUT}s por contenedor)..."
containers="$($SUDO crictl ps -q 2>/dev/null || $SUDO crictl ps 2>/dev/null | awk 'NR>1 {print $1}')"
if [ -n "$containers" ]; then
  for cid in $containers; do
    [ -z "$cid" ] && continue
    step_start=$(date +%s)
    log "[nuke] stop $cid"
    if ! timeout -k 10 "$((STOP_TIMEOUT+10))"s $SUDO crictl stop -t "$STOP_TIMEOUT" "$cid"; then
      log "[nuke] aviso: timeout al parar $cid; se fuerza eliminación"
    fi
    $SUDO crictl rm -f "$cid" || true
    log "[nuke] $cid parado/eliminado en $(( $(date +%s) - step_start ))s"
  done
else
  log "[nuke] No hay contenedores en ejecución"
fi

# 2) Borrar todos los contenedores (incl. detenidos)
log "[nuke] Borrando todos los contenedores..."
all_containers="$($SUDO crictl ps -aq || true)"
if [ -n "$all_containers" ]; then
  $SUDO crictl rm $all_containers || true
else
  log "[nuke] No hay contenedores para borrar"
fi

# 3) Parar y borrar todos los pods sandbox
log "[nuke] Parando todos los pods..."
pods="$($SUDO crictl pods -q 2>/dev/null || $SUDO crictl pods 2>/dev/null | awk 'NR>1 {print $1}')"
if [ -n "$pods" ]; then
  for pid in $pods; do
    [ -z "$pid" ] && continue
    step_start=$(date +%s)
    log "[nuke] stopp $pid"
    timeout -k 5 35s $SUDO crictl stopp "$pid" || true
    $SUDO crictl rmp -f "$pid" || true
    log "[nuke] $pid parado/eliminado en $(( $(date +%s) - step_start ))s"
  done
else
  log "[nuke] No hay pods para parar"
fi

log "[nuke] Borrando todos los pods..."
pods="$($SUDO crictl pods -q || true)"
if [ -n "$pods" ]; then
  $SUDO crictl rmp $pods || true
else
  log "[nuke] No hay pods para borrar"
fi

# 4) Podar imágenes/capas (recupera espacio)
log "[nuke] Podando imágenes..."
if ! $SUDO crictl rmi --prune; then
  images="$($SUDO crictl images -q || true)"
  if [ -n "$images" ]; then
    $SUDO crictl rmi $images || true
  else
    log "[nuke] No hay imágenes para borrar"
  fi
fi

log "[nuke] Limpieza completada. Total: $(( $(date +%s) - START_EPOCH ))s"


