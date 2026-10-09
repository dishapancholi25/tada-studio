# Release and Deployment Guide

This document describes how to release and deploy new versions of Agentic Studio to UAT and production
environments. Follow these steps exactly when asked to deploy, release, or do a rolling restart.

## CRITICAL: Always Use GitOps — Never Apply Directly to Kubernetes

> **All image tag changes and configuration changes MUST be made by updating the GitOps repository,
> never by running `kubectl set image`, `kubectl apply`, or any other command that mutates the cluster
> directly.**

The GitOps repository is the single source of truth for cluster state. Direct kubectl mutations:

- Are overwritten the next time the GitOps controller reconciles (typically within minutes)
- Leave the repository out of sync with the cluster, causing confusion and failed future deployments
- Bypass audit history and peer review

**The only kubectl commands agents are permitted to run are read-only and status commands:**

```bash
kubectl get ...
kubectl describe ...
kubectl rollout status ...
kubectl logs ...
kubectl config get-contexts
```

Do **not** run any of the following against the live clusters:

```bash
# FORBIDDEN — use GitOps instead
kubectl set image ...
kubectl apply ...
kubectl patch ...
kubectl rollout undo ...
```

`kubectl rollout restart` is permitted to force pods to pick up a freshly built image when the tag has not changed (e.g. re-deploying the same `pr-<number>` tag after new commits). Always run UAT first and confirm healthy before restarting production.

---

## Overview

- CI/CD builds Docker images via GitHub Actions and pushes them to Azure Container Registry (ACR).
- Deployments run on Azure Kubernetes Service (AKS) in the `agent-designer` namespace.
- UAT and production are separate AKS clusters managed by a GitOps controller.
- Deploying means updating the image tag in the GitOps repo and committing — the controller applies
  the change to the cluster automatically.

## GitOps Repository

The Kustomize manifests that define cluster state live in a separate repository:

```
agentic-studio-gitops
```

Environment-specific image tags are set in the overlay kustomization files:

| Environment | Overlay file |
|-------------|-------------|
| UAT         | `kubernetes/overlays/uat/kustomization.yaml` |
| Production  | `kubernetes/overlays/production/kustomization.yaml` |

## Kubernetes Contexts

These are used **for read-only verification only** — never for applying changes.

| Environment | kubectl Context              |
|-------------|------------------------------|
| UAT         | `SHAREDSERVICES-01-AKS-UAT`  |
| Production  | `SHAREDSERVICES-01-AKS-PROD` |

Check available contexts at any time:

```bash
kubectl config get-contexts
```

## Namespace and Deployments

All Agentic Studio workloads live in the `agent-designer` namespace on both clusters.

| Deployment               | UAT Replicas | Prod Replicas | Purpose              |
|--------------------------|:------------:|:-------------:|----------------------|
| `backend-deploy`         | 3            | 5             | FastAPI backend      |
| `frontend-deploy`        | 3            | 5             | Next.js frontend     |
| `flowdemoapi-deploy`     | 1            | 1             | Demo API             |
| `oauth2-proxy-deployment`| 1            | 1             | Auth proxy           |

List deployments and their current state (read-only):

```bash
kubectl get deployments -n agent-designer --context SHAREDSERVICES-01-AKS-UAT
kubectl get deployments -n agent-designer --context SHAREDSERVICES-01-AKS-PROD
```

## Container Images (ACR)

Images are stored in Azure Container Registry:

- **Registry**: `synecloudpracticeprodacr.azurecr.io`
- **Backend image**: `synecloudpracticeprodacr.azurecr.io/agenticstudio-backend:<tag>`
- **Frontend image**: `synecloudpracticeprodacr.azurecr.io/agenticstudio-frontend:<tag>`

### Image Tag Conventions

| Trigger              | Tag format      | Example       |
|----------------------|-----------------|---------------|
| Pull Request build   | `pr-<number>`   | `pr-203`      |
| Main branch build    | `latest`        | `latest`      |
| Git tag              | `<tag>`         | `v1.2.3`      |

Check the current image tags running in each environment (read-only):

```bash
kubectl get deployment backend-deploy frontend-deploy -n agent-designer \
  --context SHAREDSERVICES-01-AKS-UAT \
  -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.spec.template.spec.containers[0].image}{"\n"}{end}'
```

## CI/CD Pipeline

GitHub Actions workflows handle image builds automatically:

- **`.github/workflows/acr-build.yaml`** — builds backend and frontend images, pushes to ACR.
  - Triggers: PRs to `main`, pushes to `main`, tags, manual `workflow_dispatch`.
  - Tests must pass (via `pytest.yaml`) before images are built.
  - Runner: `arc-runner-prod`.
- **`.github/workflows/pytest.yaml`** — runs the test suite (Python 3.12/3.13 matrix).

Wait for all CI checks to pass on the PR before deploying:

```bash
gh pr checks <pr-number> --watch
```

## Deployment Procedure

**Always deploy to UAT first and confirm it is healthy before updating production.**

### 1. Confirm CI has built the image

All checks on the PR must be green, including `backend / acr-build` and `frontend / acr-build`,
before proceeding.

```bash
gh pr checks <pr-number> --watch
```

### 2. Update the UAT overlay in the GitOps repo

Edit `kubernetes/overlays/uat/kustomization.yaml` in the `agentic-studio-gitops` repository,
replacing the image tags for `backend-deploy` and `frontend-deploy` with the new PR tag:

```yaml
# kubernetes/overlays/uat/kustomization.yaml
patches:
  - target:
      kind: Deployment
      name: backend-deploy
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/image
        value: synecloudpracticeprodacr.azurecr.io/agenticstudio-backend:pr-<number>

  - target:
      kind: Deployment
      name: frontend-deploy
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/image
        value: synecloudpracticeprodacr.azurecr.io/agenticstudio-frontend:pr-<number>
```

Commit and push:

```bash
cd agentic-studio-gitops
git add kubernetes/overlays/uat/kustomization.yaml
git commit -m "chore(uat): bump image tags to pr-<number>"
git push
```

### 3. Verify UAT is healthy

Wait for the GitOps controller to reconcile and the rollout to complete, then confirm all pods
are running:

```bash
kubectl rollout status deployment/backend-deploy deployment/frontend-deploy \
  -n agent-designer --context SHAREDSERVICES-01-AKS-UAT --timeout=300s

kubectl get pods -n agent-designer --context SHAREDSERVICES-01-AKS-UAT
```

All pods should show `Running` with 0 restarts before proceeding to production.

### 4. Update the production overlay in the GitOps repo

Only once UAT is confirmed healthy, edit
`kubernetes/overlays/production/kustomization.yaml` with the same image tag and push:

```bash
cd agentic-studio-gitops
git add kubernetes/overlays/production/kustomization.yaml
git commit -m "chore(prod): bump image tags to pr-<number>"
git push
```

### 5. Verify production is healthy

```bash
kubectl rollout status deployment/backend-deploy deployment/frontend-deploy \
  -n agent-designer --context SHAREDSERVICES-01-AKS-PROD --timeout=300s

kubectl get pods -n agent-designer --context SHAREDSERVICES-01-AKS-PROD
```

## Rollback

To roll back, revert the image tag in the GitOps overlay to the previous value and push.
The GitOps controller will reconcile and the cluster will return to the previous image.

```bash
cd agentic-studio-gitops
git revert HEAD
git push
```

Or manually set the tag back to the last known good value in the overlay file and push.

## Checking Pod Health

Read-only — safe to run at any time:

```bash
# UAT
kubectl get pods -n agent-designer --context SHAREDSERVICES-01-AKS-UAT

# Production
kubectl get pods -n agent-designer --context SHAREDSERVICES-01-AKS-PROD
```

View logs for a specific pod:

```bash
kubectl logs <pod-name> -n agent-designer --context SHAREDSERVICES-01-AKS-UAT
kubectl logs <pod-name> -n agent-designer --context SHAREDSERVICES-01-AKS-PROD
```
