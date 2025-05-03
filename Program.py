import openstack
import json
from dotenv import load_dotenv
import os
import errno
from openstack.exceptions import ResourceNotFound, DuplicateResource
from prettyprinter import pprint
import time
from openstack.exceptions import ConflictException
import  requests
NOVA_URL = "https://api-ap-south-mum-1.openstack.acecloudhosting.com:8774/v2.1"
# Load environment variables
load_dotenv()
AUTH_CONFIG = {
    "auth_url": os.getenv("OPENSTACK_AUTH_URL", "https://api-ap-south-mum-1.openstack.acecloudhosting.com:5000"),
    "username": os.getenv("OPENSTACK_USERNAME", "Hackathon_AIML_1"),
    "password": os.getenv("OPENSTACK_PASSWORD", "Hackathon_AIML_1@567"),
    "project_name": os.getenv("OPENSTACK_PROJECT_NAME", "ACE_HACKATHON_AIML"),
    "user_domain_name": os.getenv("OPENSTACK_USER_DOMAIN_NAME", "Default"),
    "project_domain_name": os.getenv("OPENSTACK_PROJECT_DOMAIN_NAME", "Default")
}


def get_openstack_connection():
    """Create and return an OpenStack connection."""
    try:
        conn = openstack.connect(**AUTH_CONFIG)
        print("Successfully connected to OpenStack")
        print(f"Auth Token: {conn.auth_token}")
        return conn
    except Exception as e:
        print(f"Failed to connect to OpenStack: {str(e)}")
        return None
    
vm_name="dev-box-01",
image_name="Ubuntu-20.04",
flavor_name="S.8",   # Make sure this has enough memory
network_name="hackathon-net"
## Create  Network and Subnet
def create_network(conn):
    print("Create Network:")

    example_network = conn.network.create_network(
        name='Test-network-for-hackathon'
    )

    example_subnet = conn.network.create_subnet(
        name='aimlhack',
        network_id=example_network.id,
        ip_version='4',
        cidr='10.0.2.0/24',
        gateway_ip='10.0.2.1',
    )
                        
    return {
        "network": {
            "id": example_network.id,
            "name": example_network.name,
            "status": example_network.status,
            "project_id": example_network.project_id
        },
        "subnet": {
            "id": example_subnet.id,
            "name": example_subnet.name,
            "cidr": example_subnet.cidr,
            "gateway_ip": example_subnet.gateway_ip
        }
    }

## Projet Usage 
def project_usage(conn):
    flavors = list(conn.compute.flavors())
    flavor_map = {fl.id: fl for fl in flavors}
    flavor_map.update({fl.name: fl for fl in flavors})
    total_vcpus   = 0
    total_ram_mb  = 0
    total_gpus    = 0
    total_vol_gb  = 0

    # — vCPU, RAM, GPU via servers —
    for srv in conn.compute.servers():
        # server.flavor may be a dict like {'id': 'S.4'} or a FlavorResource
        ref = srv.flavor['id'] if isinstance(srv.flavor, dict) else srv.flavor.id
        flv = flavor_map.get(ref)
        if not flv:
            print(f"⚠️  Warning: flavor '{ref}' not found, skipping VM {srv.name}")
            continue

        total_vcpus  += flv.vcpus
        total_ram_mb += flv.ram

        # GPU detection in extra_specs (if your flavors publish GPU counts here)
        specs = getattr(flv, "extra_specs", {}) or {}
        for k, v in specs.items():
            if "gpu" in k.lower():
                try:
                    total_gpus += int(v)
                except ValueError:
                    pass

    # — Volume storage via Cinder —
    total_vol_gb = sum(vol.size for vol in conn.block_storage.volumes())

    # — Print results —
    print(f"🔹 vCPUs in use:           {total_vcpus}")
    print(f"🔹 RAM in use:             {total_ram_mb/1024:.2f} GB")
    print(f"🔹 GPUs in use (if any):   {total_gpus}")
    print(f"🔹 Volume storage in use:  {total_vol_gb} GB")


## Create Vm Instance 
def create_vm_volume_backed(conn,vm_name, image_name, flavor_name, network_name, volume_size_gb=20):
    # 1️⃣ Find required resources

    
    image = conn.compute.find_image(image_name)
    flavor = conn.compute.find_flavor(flavor_name)
    network = conn.network.find_network(network_name)

    if not image or not flavor or not network:
        print("❌ Could not find image, flavor, or network.")
        return

    print(f"\n✅ Creating bootable volume from image '{image.name}'...")

    # 2️⃣ Create a bootable volume (bootable is implicit when using image_id)
    volume = conn.block_store.create_volume(
        name=f"{vm_name}-boot-vol",
        image_id=image.id,
        size=volume_size_gb
    )

    # 3️⃣ Wait until volume is ready
    volume = conn.block_store.wait_for_status(volume, status='available', failures=['error'])
    print("✅ Volume created:", volume.id)

    # 4️⃣ Launch the instance from the volume
    print("🚀 Launching instance...")

    server = conn.compute.create_server(
        name=vm_name,
        flavor_id=flavor.id,
        networks=[{"uuid": network.id}],
        block_device_mapping_v2=[{
            "boot_index": 0,
            "uuid": volume.id,
            "source_type": "volume",
            "destination_type": "volume",
            "delete_on_termination": True
        }],
        security_groups=[{"name": "default"}]  # optional; add if security groups are used
    )

    server = conn.compute.wait_for_server(server)

    # 5️⃣ Output result
    print("\n✅ VM created successfully!")
    print("🆔 Server ID:", server.id)
    print("🌐 IP Addresses:", server.addresses)

## Resizing the Vm Instance 
def resize_vm(conn, vm_name, target_flavor_name):
    # Find server
    server = conn.compute.find_server(vm_name)
    if not server:
        print(f"❌ Server '{vm_name}' not found.")
        return

    # Find target flavor
    flavor = conn.compute.find_flavor(target_flavor_name)
    if not flavor:
        print(f"❌ Flavor '{target_flavor_name}' not found.")
        return

    # Resize the server
    try:
        print(f"🔄 Resizing '{vm_name}' to flavor '{target_flavor_name}'...")
        conn.compute.resize_server(server=server, flavor=flavor)
    except ConflictException as e:
        print(f"❌ Cannot resize: {e}")
        return

    # Wait until server enters VERIFY_RESIZE
    for _ in range(20):
        time.sleep(5)
        server = conn.compute.get_server(server.id)
        if server.status == 'VERIFY_RESIZE':
            break
    else:
        print("❌ Resize timed out or did not enter VERIFY_RESIZE.")
        return

    # Confirm resize
    try:
        print("✅ Resize in VERIFY_RESIZE state. Confirming...")
        # Use session to confirm resize
        compute_endpoint = conn.compute.get_endpoint()
        url = f"{compute_endpoint}/servers/{server.id}/action"
        payload = {"confirmResize": None}
        response = conn.session.post(url, json=payload)

        if response.status_code == 204:
            print(f"✅ Resize for '{vm_name}' to '{target_flavor_name}' confirmed successfully.")
        else:
            print(f"❌ Failed to confirm resize. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"❌ Error during confirmation: {e}")

## List Volumnes
def list_volumes(conn):
    vols = list(conn.block_storage.volumes())
    if not vols:
        print("No volumes found.")
    for v in vols:
        print(f" • Name: {v.name or '<no-name>'} | ID: {v.id} | Size: {v.size} GB | Status: {v.status}")

##
def confirm(prompt: str) -> bool:
    ans = input(f"{prompt} (yes/no): ").strip().lower()
    return ans in ("y","yes")


## Create Volume
def create_volume(conn,name: str, size_gb: int, description: str = ""):
    if not confirm(f"Create volume '{name}' ({size_gb} GB)?"):
        print("Aborted.")
        return None
    vol = conn.block_storage.create_volume(
        name=name,
        size=size_gb,
        description=description or None
    )
    # Wait until it’s available
    conn.block_storage.wait_for_status(vol, status="available", failures=["error"], interval=2, wait=120)
    print(f"✅ Volume created: {vol.id} (status={vol.status})")
    return vol

##Delete Volume 
def delete_volume(conn,vol_id: str):
    if not confirm(f"Delete volume '{vol_id}'?"):
        print("Aborted.")
        return
    conn.block_storage.delete_volume(vol_id, ignore_missing=False)
    print(f"✅ Delete requested for volume {vol_id}.")

## Delete VM Instance
def get_vm_id_by_name(name, auth_token):
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Token': auth_token
    }

    response = requests.get(f"{NOVA_URL}/servers/detail", headers=headers)
    if response.status_code == 200:
        servers = response.json().get('servers', [])
        for server in servers:
            if server['name'] == name:
                return server['id']
    return None
def delete_vm(vm_name, auth_token):
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Token': auth_token
    }

    vm_id = get_vm_id_by_name(vm_name, auth_token)
    if vm_id:
        response = requests.delete(f"{NOVA_URL}/servers/{vm_id}", headers=headers)
        if response.status_code == 204:
            print(f"VM '{vm_name}' deleted successfully.")
        else:
            print(f"Failed to delete VM: {response.status_code} - {response.text}")
    else:
        print(f"VM '{vm_name}' not found.")


def delete_vm(conn, server_name):
    # Find the server
    server = conn.compute.find_server(server_name)
    
    if not server:
        print(f"❌ Server '{server_name}' not found.")
        return

    # Confirm deletion
    confirm = input(f"⚠️ Are you sure you want to delete VM '{server_name}'? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Deletion cancelled.")
        return

    # Delete the server
    print(f"🗑️ Deleting server '{server_name}'...")
    conn.compute.delete_server(server, ignore_missing=True)
    print("✅ Server deletion initiated.")



def main():
    """Test all OpenStack service endpoints."""
    conn = get_openstack_connection()
    if not conn:
        return
    # create_vm_volume_backed(
    # vm_name="dev-box-01",
    # image_name="Ubuntu-20.04",
    # flavor_name="S.8",   # Make sure this has enough memory
    # network_name="hackathon-net"
    # )
    result = create_network(conn)
    pprint(result)
    conn.close()
if __name__ == "__main__":
    main()
    