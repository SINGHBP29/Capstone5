# Kubernetes Canary Deployment for AI Agents

This directory contains the necessary Kubernetes configuration files to manage a canary deployment of your AI agent services. This pattern allows you to test a new version of your application with a small amount of live traffic before rolling it out to all your users.

## Files

- **`deployment.yaml`**: Defines two Kubernetes `Deployments`:
  - `my-app-primary`: Represents your stable, production version (v1.0).
  - `my-app-canary`: Represents the new, candidate version you are testing (v1.1-canary).
- **`service.yaml`**: Defines a single Kubernetes `Service` that acts as the entry point for all traffic. It uses labels and selectors to control which version of your application receives traffic.
- **`kustomization.yaml`**: The entry point for the `kustomize` tool, which manages these configuration files.

## The Canary Deployment Workflow

Here is the step-by-step process for using these files to perform a safe, controlled canary release.

### Step 1: Deploy the Primary (Production) Version

First, apply the configurations to your Kubernetes cluster. This will create the `primary` deployment and the service that points to it.

```sh
kubectl apply -k .
```
At this point, 100% of your traffic is being served by the stable, v1.0 version of your application.

### Step 2: Deploy the Canary Version

The `deployment.yaml` file already contains the definition for your `canary` deployment. Since it was included in the initial `apply` command, it is already running on a single pod. However, the `my-app-service` is not yet sending any traffic to it.

### Step 3: Shift a Portion of Traffic to the Canary

This is the core of the canary test. You will now update the `my-app-service` to send a small amount of traffic to the `canary` pods. You do this by changing the service's `selector` to include both `primary` and `canary` tracks.

You can do this by applying a patch or by directly editing the `service.yaml` file to look like this:

```yaml
# In service.yaml
# ...
spec:
  # ...
  selector:
    app: my-app # Now selects all pods with the app: my-app label
```
Then, re-apply the configuration:
```sh
kubectl apply -f service.yaml
```
At this point, your Kubernetes service will automatically load-balance between the `primary` and `canary` pods. Since you have 3 primary pods and 1 canary pod, approximately **25% of traffic** will now be hitting your new version. This is the stage where your `eval_activity` and Diffy framework would be used to monitor the performance and correctness of the canary.

### Step 4A: Promote the Canary to Production

If your evaluation (the "feedback layer") determines that the canary is healthy and performing well, you can promote it to be the new production version.

1.  **Update the Image**: Change the image in your `my-app-primary` deployment to the new version (`your-app-image:v1.1-canary`).
2.  **Apply the Change**:
    ```sh
    kubectl apply -f deployment.yaml
    ```
    Kubernetes will now perform a rolling update of your `primary` pods to the new version.
3.  **Remove the Canary**: Once the rolling update is complete, you can safely delete the `my-app-canary` deployment.

### Step 4B: Roll Back the Canary

If your evaluation detects a problem (e.g., the NDCG score is too low or latency has increased), you need to roll back the canary.

1.  **Revert the Service**: Change the `service.yaml` file back so that its selector only targets the `primary` track:
    ```yaml
    # In service.yaml
    selector:
      app: my-app
      track: primary
    ```
2.  **Apply the Change**:
    ```sh
    kubectl apply -f service.yaml
    ```
    100% of your traffic will now be safely routed back to your stable, production version.
3.  **Delete the Canary**: You can now investigate the problem and safely delete the `my-app-canary` deployment.
