#!/usr/bin/env bash
set -euo pipefail

# Reinicia CRI-O y limpia estado efímero de CNI

if sudo -n true >/dev/null 2>&1; then
  SUDO="sudo -n"
else
  SUDO="sudo"
fi

START_EPOCH=$(date +%s)
log() { printf "[%s +%ss] %s\n" "$(date +%H:%M:%S)" "$(( $(date +%s) - START_EPOCH ))" "$*"; }

log "[cni] Deteniendo CRI-O para liberar netns..."
$SUDO systemctl stop crio

log "[cni] Borrando caché/estado temporal de CNI..."
$SUDO rm -rf /var/lib/cni/networks/* /var/run/cni/* || true

log "[cni] Eliminando netns huérfanas de CNI..."
ns_list=$(ip netns list 2>/dev/null | awk '/cni-|ns-/{print $1}' || true)
if [ -n "${ns_list:-}" ]; then
  echo "$ns_list" | while read -r ns; do
    [ -z "$ns" ] && continue
    $SUDO ip netns delete "$ns" || true
  done
else
  log "[cni] No hay netns huérfanas"
fi

log "[cni] Intentando eliminar bridges/túneles comunes..."
$SUDO ip link del cni0       2>/dev/null || true
$SUDO ip link del flannel.1  2>/dev/null || true
$SUDO ip link del weave      2>/dev/null || true
$SUDO ip link del cilium_host 2>/dev/null || true

log "[cni] Arrancando CRI-O de nuevo..."
$SUDO systemctl start crio

log "[cni] Arrancando kubelet (si aplica)..."
$SUDO systemctl start kubelet || true

log "[cni] Limpieza y reinicio completados. Total: $(( $(date +%s) - START_EPOCH ))s"


