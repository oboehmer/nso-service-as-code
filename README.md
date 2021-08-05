# NSO Service as Code

This is a "Network as Code" CICD pipeline which provisions a Layer2VPN p2p/VPWS service onto a IOS-XE network via NSO.
This example demonstrate on how to use NSO to maintain network service configurations via a CICD pipeline, supporting create, update and delete operations on the service.

The repository hosts the customer service data in the [l2vpn/](l2vpn/) directory as one yaml file per customer, any changes to these files (actually to all files in the repo) will trigger a CICD pipeline which provisions the service(s) on the network.  
Only changes in master will provision the changes in the network, non-master branches trigger a so-called dry-run commit which only verifies the service data, but not perform any changes on the network.

The main purpose of this is to show the power of NSO when used within a Network as Code use case. It's FASTMAP capabilities can keep the pipeline very simple as all the additions, changes and deletions are handled within NSO.

The pipeline invokes the Python script ([scripts/provision.py](scripts/provision.py)) which essentially does the following:

1. Retrieves all currently provisioned customers with this service
2. Reads each service file (i.e. l2vpn/cust1.yaml) and pushes the service data using a RESTCONF PUT request (with all service instances for this customer). This PUT requests triggers NSO to derive all the required changes and implements them in the network devices. 
3. Finally the script deletes all customers which have not been touched in step 2 (to cater for a deletion of a yaml file)

TODO: Add a step to verify the deployed services using pyATS script.

