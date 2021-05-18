# Stack References

Use stack references to pass information from one stack to another.  
There are two project directories: base_infra and app.

- base_infra: stands up a base AKS cluster and exports the kubeconfig.
- app: deploys a simple app on a K8s cluster.

## Main Exercise

- Add stack references to the `app` project to get the kubeconfig from the the `base_infra` stack.
- In each directory, run `pulumi stack init` to initialize a stack for each project.
- In `base_infra` run `pulumi up` to launch the base infrastructure stack.
- In `app` run `pulumi up` to launch the app on the base infrastructure.

See the prolog section of the main program file for the exercises.

See the `solutions` folder for the answers.
