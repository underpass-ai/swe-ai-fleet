#!/usr/bin/env bash
set -euo pipefail

# Kubernetes + Calico diagnostics helper
# Usage: ./scripts/k8s_calico_diag.sh [output_log]
# If output_log is omitted, a timestamped log will be created in the current directory.

OUT="${1:-k8s_calico_diag_$(date +%Y%m%d_%H%M%S).log}"

log() {
  echo -e "\n===== $* =====" | tee -a "$OUT"
}

run() {
  # Print the command and append both stdout and stderr to the log
  echo "+ $*" | tee -a "$OUT"
  eval "$*" 2>&1 | tee -a "$OUT" || true
}

run_sudo() {
  if sudo -n true 2>/dev/null; then
    run "sudo $*"
  else
    run "$*"
  fi
}

log "Environment"
run "kubectl version --client || true"
run "crio --version || true"

log "Nodes"
run "kubectl get nodes -o wide"

log "kube-system pods (Calico, CoreDNS, control plane)"
run "kubectl -n kube-system get pods -o wide | grep -E 'calico|coredns|kube-|etcd' || true"

log "Calico DaemonSet and Deployment"
run "kubectl -n kube-system get ds calico-node -o wide || true"
run "kubectl -n kube-system get deploy calico-kube-controllers -o wide || true"

log "kube-system recent events"
run "kubectl -n kube-system get events --sort-by=.lastTimestamp | tail -n 50"

# Resolve pod names
CALICO_NODE_POD="$(kubectl -n kube-system get pods -l k8s-app=calico-node -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
CALICO_CTRL_POD="$(kubectl -n kube-system get pods -l k8s-app=calico-kube-controllers -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"

if [[ -n "${CALICO_NODE_POD}" ]]; then
  log "Describe calico-node pod: ${CALICO_NODE_POD}"
  run "kubectl -n kube-system describe pod ${CALICO_NODE_POD} | sed -n '1,200p'"
  log "Logs: calico-node init container install-cni (tail)"
  run "kubectl -n kube-system logs ${CALICO_NODE_POD} -c install-cni --tail=200"
  log "Logs: calico-node main container (tail)"
  run "kubectl -n kube-system logs ${CALICO_NODE_POD} -c calico-node --tail=200"
else
  log "No calico-node pod found"
fi

if [[ -n "${CALICO_CTRL_POD}" ]]; then
  log "Describe calico-kube-controllers pod: ${CALICO_CTRL_POD}"
  run "kubectl -n kube-system describe pod ${CALICO_CTRL_POD} | sed -n '1,200p'"
  log "Logs: calico-kube-controllers (tail)"
  run "kubectl -n kube-system logs ${CALICO_CTRL_POD} --tail=200"
else
  log "No calico-kube-controllers pod found"
fi

log "Host CNI directories and configs"
run_sudo "ls -ld /etc/cni/net.d /opt/cni/bin"
run_sudo "ls -l /etc/cni/net.d || true"
run_sudo "ls -l /opt/cni/bin | egrep 'calico|loopback|host-local|portmap' || true"
for f in /etc/cni/net.d/*; do
  if [[ -f "$f" ]]; then
    log "CNI config: $f"
    run_sudo "cat $f"
  fi
done

log "Kernel/sysctl required by CNI"
run "sysctl net.ipv4.ip_forward || true"
run "lsmod | grep br_netfilter || true"
run "sysctl net.bridge.bridge-nf-call-iptables net.bridge.bridge-nf-call-ip6tables || true"

log "Node detail (taints/conditions/addresses)"
NODE_NAME="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"
run "kubectl describe node ${NODE_NAME} | sed -n '1,200p'"

log "Calico CRDs (ippools, felixconfigurations)"
run "kubectl get ippools.crd.projectcalico.org -A -o wide || true"
run "kubectl get felixconfigurations.crd.projectcalico.org -A -o yaml | sed -n '1,120p' || true"

echo "\nDiagnostics written to: $OUT"


