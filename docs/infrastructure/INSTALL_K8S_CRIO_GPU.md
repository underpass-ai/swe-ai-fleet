# Kubernetes con CRI-O y NVIDIA GPU Operator — Guía de instalación

Esta guía describe cómo instalar un clúster de Kubernetes usando CRI‑O como runtime de contenedores y habilitar GPUs NVIDIA mediante el NVIDIA GPU Operator. Está orientada a una estación Linux (ej. Arch Linux) pero incluye notas para otras distros.

## Estrategia de instalación — por qué instalar primero las herramientas de Kubernetes

Antes de inicializar el clúster, instalamos primero las herramientas base de Kubernetes (kubeadm, kubelet, kubectl) y Helm por los siguientes motivos:

- Dependencias previas: `kubeadm` y `kubelet` son necesarios para el `init` del plano de control y para gestionar el servicio de nodo.
- Servicio persistente: habilitar `kubelet` de antemano evita pasos adicionales tras el `init` y facilita diagnósticos si algo falla.
- Helm como estándar: el NVIDIA GPU Operator, Ingress NGINX y otros componentes se instalan cómodamente con Helm; tenerlo listo simplifica el flujo.
- Idempotencia y bajo riesgo: la instalación de binarios no modifica el estado del clúster; es segura de ejecutar incluso si la inicialización se difiere.
- Trazabilidad y soporte: confirmar versiones (kubeadm/kubectl/helm) al inicio reduce variables en la resolución de problemas.

Comandos ejecutados (Arch Linux):

```bash
sudo pacman -S --noconfirm kubeadm kubelet kubectl helm
sudo systemctl enable --now kubelet

# Verificar versiones
kubeadm version -o short
kubectl version --client
helm version --short
```

> Importante: hasta este punto solo hemos instalado y habilitado las herramientas. **Aún NO hemos configurado/inicializado el clúster** (no se ha ejecutado `kubeadm init`). La configuración del clúster comienza en el siguiente apartado.

## Requisitos

- Host Linux con privilegios de administrador
- GPU(s) NVIDIA compatibles
- Kernel y drivers NVIDIA instalados en el host, o permitir que el GPU Operator gestione los drivers
- Paquetes: CRI‑O, kubeadm, kubelet, kubectl

Notas:
- Para un entorno estable, recomendamos drivers NVIDIA instalados a nivel de host y desplegar SOLO Device Plugin + Toolkit desde el Operator (driver.enabled=false). Alternativamente, el Operator puede gestionar los drivers.
- CRI‑O es el runtime preferido del proyecto; evitamos dockershim.

## 1) Instalar CRI‑O

Arch Linux (ejemplo):

```bash
sudo pacman -S --noconfirm cri-o crun conmon containers-common skopeo buildah
sudo systemctl enable --now crio
sudo systemctl status crio | cat
```

Otras distros: seguir la documentación oficial de CRI‑O para su versión de Kubernetes.

### Acceso rootless al socket de CRI‑O (opcional recomendado)

Permite usar `crictl` y herramientas cliente sin `sudo` asegurando permisos en `/run/crio/crio.sock`.

1) Crear grupo y añadir tu usuario (cierra sesión o usa `newgrp` después):

```bash
sudo groupadd -f crio
sudo usermod -aG crio "$USER"
```

2) Arch Linux y otras distros sin `crio.socket`: drop‑in para `crio.service` que fija permisos del socket tras el arranque.

```bash
sudo mkdir -p /etc/systemd/system/crio.service.d
cat <<'EOF' | sudo tee /etc/systemd/system/crio.service.d/10-sock-perms.conf
[Service]
ExecStartPost=/bin/sh -c 'for i in $(seq 1 20); do \
  [ -S /run/crio/crio.sock ] && { chgrp crio /run/crio/crio.sock && chmod 660 /run/crio/crio.sock && exit 0; }; \
  sleep 0.2; done; exit 0'
EOF

sudo systemctl daemon-reload
sudo systemctl restart crio
```

3) Si tu distro sí provee `crio.socket`, puedes usar override sobre el unit de socket:

```bash
sudo mkdir -p /etc/systemd/system/crio.socket.d
cat <<'EOF' | sudo tee /etc/systemd/system/crio.socket.d/override.conf
[Socket]
SocketMode=0660
SocketUser=root
SocketGroup=crio
EOF
sudo systemctl daemon-reload
sudo systemctl restart crio.socket
sudo systemctl restart crio
```

4) Refrescar el grupo en la shell actual y validar:

```bash
newgrp crio <<'EOF'
crictl version
EOF
```

Salida esperada (ejemplo):

```
Version:  0.1.0
RuntimeName:  cri-o
RuntimeVersion:  1.33.4
RuntimeApiVersion:  v1
```

Nota: si sigues viendo `permission denied`, aplica una ACL temporal y reintenta (útil hasta el próximo arranque):

```bash
sudo setfacl -m u:$USER:rw /run/crio/crio.sock
```

## 2) Instalar Kubernetes (kubeadm/kubelet/kubectl)

Arch Linux (ejemplo):

```bash
sudo pacman -S --noconfirm kubeadm kubelet kubectl
sudo systemctl enable kubelet
```

Preparación del sistema (común):

```bash
sudo swapoff -a
sudo sed -i.bak '/\sswap\s/d' /etc/fstab

# Módulos y sysctl de red
cat <<'EOF' | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay || true
sudo modprobe br_netfilter || true

cat <<'EOF' | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
sudo sysctl --system
```

Configurar kubelet para CRI‑O:

```bash
sudo mkdir -p /etc/systemd/system/kubelet.service.d
cat <<'EOF' | sudo tee /etc/systemd/system/kubelet.service.d/10-crio.conf
[Service]
Environment="KUBELET_EXTRA_ARGS=--container-runtime-endpoint=unix:///var/run/crio/crio.sock"
EOF

sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

## 3) Inicializar el clúster con kubeadm

Elegir un CIDR de red de Pods (ej. 10.244.0.0/16 para Calico/Flannel). En el nodo maestro/control-plane:

```bash
sudo kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --cri-socket=unix:///var/run/crio/crio.sock
```

Configurar kubectl para el usuario actual:

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl get nodes -o wide
```

Guardar el comando `kubeadm join` que imprime la salida para unir nodos worker.

## 4) Instalar CNI (Calico) con CRI‑O — guía práctica y resolución de problemas

### 4.1 Aplicar manifiestos de Calico

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.3/manifests/calico.yaml
```

### 4.2 Alinear Calico con CRI‑O (ruta de binarios CNI)

En CRI‑O, los binarios CNI efectivos suelen estar en `/usr/lib/cni`. Calico por defecto instala en `/opt/cni/bin`. Si no se alinean, los pods salen solo con loopback (127.0.0.1) y Calico entra en CrashLoop al no poder contactar al API.

Recomendado: instruir al initContainer `install-cni` del DaemonSet `calico-node` a copiar también en `/usr/lib/cni` y a generar la conf en `/etc/cni/net.d`.

```bash
# Añade variables al initContainer y un volumen hostPath a /usr/lib/cni
kubectl -n kube-system patch ds calico-node --type=strategic -p '
spec:
  template:
    spec:
      initContainers:
      - name: install-cni
        env:
        - name: CNI_BIN_DIR
          value: /usr/lib/cni
        - name: CNI_CONF_DIR
          value: /etc/cni/net.d
        volumeMounts:
        - name: host-cni-lib
          mountPath: /host/usr/lib/cni
      volumes:
      - name: host-cni-lib
        hostPath:
          path: /usr/lib/cni
          type: DirectoryOrCreate
'

# (Opcional, robustez) Monta también /usr/lib/cni como destino secundario que el instalador utiliza
kubectl -n kube-system patch ds calico-node --type=strategic -p '
spec:
  template:
    spec:
      initContainers:
      - name: install-cni
        volumeMounts:
        - name: host-cni-lib
          mountPath: /host/secondary-bin-dir
'
```

Alternativa: en lugar de parchear Calico, puedes configurar CRI‑O para buscar también en `/opt/cni/bin` añadiéndolo a `plugin_dirs` en `/etc/crio/crio.conf`, y reiniciar CRI‑O. Aun así, recomendamos la opción anterior para mantener el estándar de CRI‑O.

### 4.3 Limpieza de configuraciones CNI y pool de pods

Calico debe crear `10-calico.conflist` en `/etc/cni/net.d`. Para evitar conflictos por orden lexicográfico, deja solo loopback antes de reiniciar Calico.

```bash
sudo mkdir -p /etc/cni/net.d
sudo find /etc/cni/net.d -maxdepth 1 -type f ! -name '00-loopback.conf' -delete

# Asegura el CIDR de pods coherente con kubeadm init (10.244.0.0/16)
kubectl -n kube-system set env ds/calico-node CALICO_IPV4POOL_CIDR=10.244.0.0/16 --overwrite

# Reinicia calico-node para que el initContainer re‑instale CNI
kubectl -n kube-system rollout restart ds/calico-node
```

Verifica que se han instalado binarios y conf:

```bash
kubectl -n kube-system logs ds/calico-node -c install-cni --tail=200
ls -l /usr/lib/cni | grep -E 'calico|calico-ipam|portmap|tuning|bandwidth' || true
ls -l /etc/cni/net.d
# Esperado: 00-loopback.conf y 10-calico.conflist (+ calico-kubeconfig)
```

### 4.4 Bootstrap si el Service `kubernetes` (10.96.0.1:443) no es alcanzable desde pods

En bootstraps lentos, `calico-kube-controllers` puede fallar inicializando el datastore por timeouts al API. Puedes forzar temporalmente las variables del API y/o el ConfigMap para evitar depender del ClusterIP hasta que CNI esté listo:

```bash
# Establece host/port del API server (sustituye por tu IP de control-plane)
API_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

kubectl -n kube-system create configmap kubernetes-services-endpoint \
  --from-literal=KUBERNETES_SERVICE_HOST=$API_IP \
  --from-literal=KUBERNETES_SERVICE_PORT=6443 \
  --dry-run=client -o yaml | kubectl -n kube-system apply -f -

kubectl -n kube-system set env ds/calico-node \
  KUBERNETES_SERVICE_HOST=$API_IP KUBERNETES_SERVICE_PORT=6443 --overwrite
kubectl -n kube-system set env deploy/calico-kube-controllers \
  KUBERNETES_SERVICE_HOST=$API_IP KUBERNETES_SERVICE_PORT=6443 --overwrite

kubectl -n kube-system rollout restart ds/calico-node
kubectl -n kube-system rollout restart deploy/calico-kube-controllers
```

Cuando CNI esté operativo y kube‑proxy haya programado NAT, puedes revertir estas envs si lo deseas.

### 4.5 Reinicio de kubelet y reciclado de pods clave

```bash
sudo systemctl restart kubelet
kubectl -n kube-system delete pod -l k8s-app=calico-kube-controllers
kubectl -n kube-system delete pod -l k8s-app=kube-dns
```

### 4.6 Verificación

```bash
kubectl -n kube-system get pods -o wide | grep -E 'calico|coredns'
# IPs de pods deben ser 10.244.x.y, no 127.0.0.1

kubectl get nodes -o wide
```

Opcional: prueba de red desde un pod (si tu nodo es sólo control‑plane, quita taints o añade tolerations).

```bash
# Quitar taints (laboratorio)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
kubectl taint nodes --all node-role.kubernetes.io/master-

# Pod de prueba
kubectl run -n default netshoot --image=nicolaka/netshoot --restart=Never -it -- \
  sh -c 'ip -o -4 a; nc -vz kubernetes.default.svc 443 || true; \
  wget -qO- https://kubernetes.default.svc/healthz --no-check-certificate \
    --header "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" && echo'
```

### 4.7 Diagnóstico (script)

Incluimos un script para recolectar diagnósticos de Calico/CNI/CRI‑O:

```bash
scripts/k8s_calico_diag.sh
```

Genera un log con estado de nodos, pods, eventos, describe/logs de calico, contenidos de `/etc/cni/net.d` y binarios CNI.

> Nota: Si en algún momento reaparece una CNI previa (p. ej. `10-crio-bridge.conflist`) en `/etc/cni/net.d`, elimínala o renómbrala (mantén sólo `00-loopback.conf` y la `10-calico.conflist`). CRI‑O selecciona por orden lexicográfico.

### 4.8 Kustomize (persistir el patch de Calico en repositorio)

Para que los ajustes del initContainer `install-cni` (CNI_BIN_DIR, mounts a `/usr/lib/cni`) no se pierdan al actualizar, versiona un overlay con Kustomize:

Estructura:

```
deploy/kustomize/calico/
  kustomization.yaml
  calico-node-cni-patch.yaml
```

`deploy/kustomize/calico/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - https://raw.githubusercontent.com/projectcalico/calico/v3.27.3/manifests/calico.yaml
patchesStrategicMerge:
  - calico-node-cni-patch.yaml
```

`deploy/kustomize/calico/calico-node-cni-patch.yaml`:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: calico-node
  namespace: kube-system
spec:
  template:
    spec:
      initContainers:
        - name: install-cni
          env:
            - name: CNI_BIN_DIR
              value: /usr/lib/cni
            - name: CNI_CONF_DIR
              value: /etc/cni/net.d
          volumeMounts:
            - name: host-cni-lib
              mountPath: /host/usr/lib/cni
            - name: host-cni-lib
              mountPath: /host/secondary-bin-dir
      volumes:
        - name: host-cni-lib
          hostPath:
            path: /usr/lib/cni
            type: DirectoryOrCreate
```

Aplicación:

```bash
kubectl apply -k deploy/kustomize/calico/
```

### 4.9 Troubleshooting futuro (si reaparece el problema)

Si un pod aparece con IP `127.0.0.1` o `<none>`, revisa:

```bash
# 1) Logs del instalador CNI de Calico
kubectl -n kube-system logs ds/calico-node -c install-cni --tail=200

# 2) Binarios CNI que CRI‑O usa (típico /usr/lib/cni)
ls -l /usr/lib/cni | grep -E 'calico|calico-ipam'

# 3) Confs CNI efectivas
ls -l /etc/cni/net.d | grep calico
```

Asegura que NO exista otra CNI con nombre lexicográficamente menor (por ejemplo `05-*.conf`) en `/etc/cni/net.d`, ya que CRI‑O selecciona la primera. Mantén solo `00-loopback.conf` y `10-calico.conflist`.



## 5) NVIDIA GPU Operator

Añadir el repositorio Helm e instalar el Operator. Dos variantes:

### Variante A (drivers ya instalados en el host) — recomendado

```bash
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update

kubectl create namespace nvidia-gpu-operator || true

helm upgrade --install gpu-operator nvidia/gpu-operator \
  --namespace nvidia-gpu-operator \
  --set driver.enabled=false \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true
```

### Variante B (Operator gestiona drivers)

```bash
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update

kubectl create namespace nvidia-gpu-operator || true

helm upgrade --install gpu-operator nvidia/gpu-operator \
  --namespace nvidia-gpu-operator
```

Notas:
- El Operator detecta CRI‑O automáticamente. En versiones recientes, genera especificaciones **CDI** para CRI‑O, exponiendo `nvidia.com/gpu` como recurso.
- Verificar que los pods del Operator estén en Running:

```bash
kubectl get pods -n nvidia-gpu-operator -o wide
```

## 6) Validación de GPU en el clúster

Verificar que el nodo expone recursos GPU:

```bash
kubectl describe node $(kubectl get nodes -o name | head -n1) | grep -i -E "nvidia.com/gpu|cdi.k8s.io"
```

Ejecutar un Pod de prueba con `nvidia-smi`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-smoke
spec:
  restartPolicy: Never
  containers:
    - name: nvidia-smi
      image: nvidia/cuda:12.2.0-base-ubuntu22.04
      command: ["/bin/bash","-lc","nvidia-smi && sleep 5"]
      resources:
        limits:
          nvidia.com/gpu: 1
```

Aplicar y revisar logs:

```bash
kubectl apply -f gpu-smoke.yaml
kubectl logs -f pod/gpu-smoke
```

Salida esperada: tabla de `nvidia-smi` con la(s) GPU(s).

## 7) Unir nodos worker (opcional)

En cada worker con CRI‑O y kubelet configurados, ejecutar el `kubeadm join ...` que imprimió el init. Si se perdió, puede regenerarse:

```bash
sudo kubeadm token create --print-join-command
```

## 8) Integración con EdgeCrew/EdgeFleet

- Esta configuración cumple los requisitos de la fase Kubernetes del proyecto. Las guías de despliegue en `deploy/helm/` asumen Redis/Neo4j/vLLM como Services en el clúster.
- Para GPU con vLLM, utilizar un Deployment con `resources.limits["nvidia.com/gpu"]` y confirmar compatibilidad con el Operator.

## Solución de problemas

- CRI‑O no responde: `journalctl -u crio -e`, `sudo crictl info`.
- Kubelet CrashLoop: confirmar endpoint CRI y cgroup driver (`systemd`) alineado con CRI‑O.
- CNI no levanta: revisar manifiesto de Calico y que el `pod-network-cidr` coincide.
- GPU no visible:
  - Verificar drivers en el host o estado del DaemonSet del driver (variante B).
  - Confirmar `toolkit` y `device-plugin` en Running.
  - Reintentar el Pod de prueba y revisar `kubectl describe pod` por errores de asignación de recursos.

### 8.1 Troubleshooting general (end‑to‑end)

Diagnóstico rápido:

```bash
# CRI‑O rootless / crictl
crio --version && crictl version

# Estado del clúster y kube-system
kubectl get nodes -o wide
kubectl -n kube-system get pods -o wide
kubectl -n kube-system get events --sort-by=.lastTimestamp | tail -n 50

# kube-proxy
kubectl -n kube-system get ds kube-proxy -o wide
kubectl -n kube-system logs ds/kube-proxy --tail=200 | grep -i -E 'error|iptables|ipvs' || true
```

Problemas típicos y arreglos:

- Pods con IP `127.0.0.1` o `<none>` (CNI):
  - Causa: Calico instalando en `/opt/cni/bin` y CRI‑O buscando en `/usr/lib/cni`; o existe otra CNI que se adelanta.
  - Fix rápido:
    ```bash
    # Ver binarios/calico y confs
    kubectl -n kube-system logs ds/calico-node -c install-cni --tail=200
    ls -l /usr/lib/cni | grep -E 'calico|calico-ipam'
    ls -l /etc/cni/net.d

    # Mantener sólo loopback antes de reinstalar conf
    sudo find /etc/cni/net.d -maxdepth 1 -type f ! -name '00-loopback.conf' -delete

    # Parche de Calico (initContainer) para copiar en /usr/lib/cni
    kubectl apply -k deploy/kustomize/calico/

    # Reinicios
    kubectl -n kube-system rollout restart ds/calico-node
    sudo systemctl restart kubelet
    kubectl -n kube-system delete pod -l k8s-app=kube-dns
    kubectl -n kube-system delete pod -l k8s-app=calico-kube-controllers
    ```

- Calico kube-controllers `CrashLoopBackOff` con `dial tcp 10.96.0.1:443 i/o timeout`:
  - Causa: intenta usar el Service `kubernetes` antes de tener red.
  - Fix temporal (bootstrap): forzar `KUBERNETES_SERVICE_HOST/PORT` al IP:6443 del API y reiniciar; luego revertir si se desea.
    ```bash
    API_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
    kubectl -n kube-system create configmap kubernetes-services-endpoint \
      --from-literal=KUBERNETES_SERVICE_HOST=$API_IP \
      --from-literal=KUBERNETES_SERVICE_PORT=6443 \
      --dry-run=client -o yaml | kubectl -n kube-system apply -f -
    kubectl -n kube-system set env deploy/calico-kube-controllers KUBERNETES_SERVICE_HOST=$API_IP KUBERNETES_SERVICE_PORT=6443 --overwrite
    kubectl -n kube-system rollout restart deploy/calico-kube-controllers
    ```

- CoreDNS en CrashLoop / IP 127.0.0.1:
  - Causa: CNI aún no configurado.
  - Fix: aplicar los pasos de CNI, borrar pods `kube-dns` para que relancen con eth0 y reintentar.

- Pod de prueba `Pending` en clúster de 1 nodo (control-plane):
  - Quitar taints (lab) o usar tolerations para el Pod.
    ```bash
    # Lab
    kubectl taint nodes --all node-role.kubernetes.io/control-plane- || true
    kubectl taint nodes --all node-role.kubernetes.io/master- || true

    # Tolerations en Pod (alternativa)
    kubectl run -n default netshoot --image=nicolaka/netshoot --restart=Never -it \
      --overrides='{"apiVersion":"v1","spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}' -- sh
    ```

- kube-proxy con iptables/ipvs:
  - Verifica que se ejecuta y sin errores; en IPVS carga módulos `ip_vs*` y `nf_conntrack`.

Checklist de sysctls/módulos mínimos:

```bash
sudo modprobe br_netfilter overlay
sudo sysctl -w net.bridge.bridge-nf-call-iptables=1
sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=1
sudo sysctl -w net.ipv4.ip_forward=1
```

## Referencias

- CRI‑O: `https://cri-o.io/`
- kubeadm: `https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/`
- Calico: `https://projectcalico.docs.tigera.io/`
- NVIDIA GPU Operator: `https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/`


