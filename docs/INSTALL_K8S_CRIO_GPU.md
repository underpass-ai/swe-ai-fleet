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

## 4) Instalar un CNI (Calico recomendado)

Ejemplo con Calico:

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.3/manifests/calico.yaml
kubectl -n kube-system get pods
```

Esperar a que el plano de control y el CNI estén en estado Ready.

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

## Referencias

- CRI‑O: `https://cri-o.io/`
- kubeadm: `https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/`
- Calico: `https://projectcalico.docs.tigera.io/`
- NVIDIA GPU Operator: `https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/`


