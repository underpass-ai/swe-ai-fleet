## Planning UI gRPC Module Failure — Deep Dive (2025-11-28)

### 1. Context
- Runtime error observed in `planning-ui` pods after redeploy:
  `ReferenceError: require is not defined in ES module scope` → addressed earlier by forcing CommonJS boundary.
- New failure (current logs) reports `Cannot find module 'google-protobuf'` while loading `/app/gen/fleet/planning/v2/planning_grpc_pb.js`.
- Goal: explain why the dependency is still missing inside the running pods even after adding it to `package.json` and rebuilding.

### 2. Evidence Collected
1. **Cluster logs (post-redeploy)**
   ```
   kubectl logs -n swe-ai-fleet deployment/planning-ui
   -> repeated "Cannot find module 'google-protobuf'" stack traces
   ```
   Confirms pods running in the cluster still lack the dependency at runtime.

2. **Local image inspection**
   ```
   podman run --rm registry.underpassai.com/swe-ai-fleet/planning-ui:v0.1.0 \
     /bin/sh -c "cd /app && npm ls google-protobuf"
   -> google-protobuf@3.21.4 present
   ```
   The freshly built/pushed image *does* contain `google-protobuf`, so the build pipeline is correct.

3. **Pod image digest vs. local digest**
   - Pod:
     ```
     kubectl get pod planning-ui-795885b8db-kjxc9 -n swe-ai-fleet \
       -o jsonpath='{.status.containerStatuses[0].imageID}'
     -> registry.underpassai.com/...@sha256:90b76c...
     ```
   - Local image just built/pushed:
     ```
     podman inspect registry.underpassai.com/.../planning-ui:v0.1.0 -f '{{.Digest}}'
     -> sha256:839dc1868649665...
     ```
   - **Mismatch** shows the cluster is still running an *older* digest even though the tag is the same (`v0.1.0`).

4. **In-pod dependency check**
   ```
   kubectl exec planning-ui-795885b8db-kjxc9 -- /bin/sh -c "cd /app && npm ls google-protobuf"
   -> (empty) / command fails
   ```
   Confirms the pod’s filesystem truly lacks the dependency.

### 3. Root Cause
- Tag reuse (`v0.1.0`) combined with the private registry’s caching behavior caused the cluster to pull an *older* image digest (`sha256:90b7...`) that predates the `google-protobuf` addition.
- Despite `imagePullPolicy: Always`, Kubernetes will continue running the already-downloaded digest until we force nodes to evict it (or change the tag/digest).
- Therefore the redeploy never actually picked up the new filesystem contents, so the CommonJS boundary fix deployed, but the dependency addition did not.

### 4. Remediation Plan
1. **Publish a unique tag** (e.g., `v0.1.0-20251128-0904` or bump semantic version to `v0.1.3`). Push and update `deploy/k8s/.../planning-ui.yaml` (or apply a `kubectl set image`) to reference the new tag. This guarantees kube pulls the new digest.
2. Optional but recommended:
   - `kubectl delete pod --all -l app=planning-ui -n swe-ai-fleet` after updating the tag so every node drops cached layers.
   - Alternatively, `crictl rmi` on the nodes, but tag bump is simpler.
3. After redeploy, re-run:
   - `kubectl logs deployment/planning-ui -n swe-ai-fleet` (should show only the Astro startup banner).
   - `kubectl exec ... npm ls google-protobuf` to confirm dependency exists.

### 4.1 Actions Executed (2025-11-28 @ 09:11 CET)
- Tagged the fixed image as `registry.underpassai.com/swe-ai-fleet/planning-ui:v0.1.0-20251128-0905` and pushed it.
- Updated the deployment via  
  ```
  kubectl set image deployment/planning-ui \
    planning-ui=registry.underpassai.com/swe-ai-fleet/planning-ui:v0.1.0-20251128-0905 \
    -n swe-ai-fleet
  ```
- Rollout succeeded; new pods `planning-ui-7945847f68-{6kgjv,swhhm}` report image digest `sha256:86a4a7c46ed...`.
- Runtime verification:
  - `kubectl logs planning-ui-7945847f68-6kgjv` → only Astro startup banner, no module errors.
  - `kubectl exec ... npm ls google-protobuf` → dependency present (`google-protobuf@3.21.4`).
- Old pods with digest `sha256:90b7...` terminated; deployment now clean.

### 5. Preventive Actions
- Adopt immutable tagging policy (include git SHA or timestamp) and reference that tag in K8s manifests. Avoid reusing `v0.1.0` for multiple builds.
- Add a CI/CD gate that compares the digest returned by `kubectl get pod ... -o jsonpath='{.status.containerStatuses[0].imageID}'` against the digest produced by `podman inspect` to ensure deployments pick up the correct artifact.
- Optionally enable admission control that rejects deployments pointing to mutable tags (enforce digests).

### 6. Next Steps Checklist
| Status | Action |
| --- | --- |
| ☐ | Build + push image with new immutable tag containing CommonJS + `google-protobuf`. |
| ☐ | Update K8s deployment manifest (or use `kubectl set image`) to point at new tag. |
| ☐ | Redeploy & verify logs/pod contents. |
| ☐ | Document tagging policy in `docs/RELEASE.md` (or relevant runbook). |

