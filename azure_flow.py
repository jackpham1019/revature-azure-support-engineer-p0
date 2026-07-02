import subprocess
import os
import sys

def run_linux_command(command_list):
    """Utility function to safely execute a Linux command array"""
    print(f"Executing: {' '.join(command_list)}")
    try:
        # run() executes the command and waits for it to complete
        result = subprocess.run(command_list, check=True, text=True, capture_output=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"\n Error executing command!", file=sys.stderr)
        print(f"Error Code: {e.returncode}", file=sys.stderr)
        print(f"Details: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def run_az_command(command_list):
    """Utility function to safely execute an Azure CLI command array"""
    print(f"Executing: {' '.join(command_list)}")
    try:
        result = subprocess.run(command_list, check=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed with return code {e.returncode}!", file=sys.stderr)
        print(f"Details: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def main():
    print("=== Azure SRE DOcker Compose Automated Deployment Pipeline using Python ===")

    # 1. Capture user inputs
    rg_name = input("Enter Resource Group [rg-project-0]: ").strip() or "rg-project-0"
    vm_name = input("Enter VM Name [vm-appserver-project-0]: ").strip() or "vm-appserver-project-0"
    nsg_name = f"{vm_name}-NSG"
    location = input("Enter Region [canadaeast]: ").strip() or "canadaeast"
    port = "8081"
    ssh_key_path = os.path.expanduser(f"~/.ssh/{rg_name}_{vm_name}_key")
    source_bootstrap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bootstrap_vm.sh")

    if not os.path.exists(ssh_key_path):
        generate_ssh_key_cm = [
            "ssh-keygen", 
            "-t", "rsa", 
            "-b", "4096",
            "-f", ssh_key_path, 
            "-N", ""]  # Generate SSH key pair for the VM
        run_linux_command(generate_ssh_key_cm)
    else:
        print(f"SSH key already exists: {ssh_key_path}")

    print(f"\nConfiguration:")
    print(f"- Resource Group: {rg_name}")
    print(f"- VM Name: {vm_name}")
    print(f"- Location: {location}")
    print(f"- Exposed Port: {port}\n")

    # 2. Create Resource Group
    print("=== 2. Ensuring Resource Group Exists ===")
    create_rg_cmd = ["az", "group", "create", "--name", rg_name, "--location", location, "--output", "table"]
    run_az_command(create_rg_cmd)

    # 3. Create VM 
    check_vm_cmd = ["az", "vm", "list", "-g", rg_name, "--query", f"[?name=='{vm_name}'].name", "-o", "tsv"]
    vm_check_output = run_az_command(check_vm_cmd).strip()

    if not vm_check_output:
        print(f"VM {vm_name} not found. Provisioning now...")
        create_vm_cmd = [
            "az", "vm", "create", 
            "--resource-group", rg_name,
            "--name", vm_name,
            "--nsg", nsg_name,
            "--image", "Ubuntu2204",
            "--size", "Standard_B2ats_v2",
            "--storage-sku", "Standard_LRS",
            "--boot-diagnostics-storage", "",
            "--admin-username", "azureuser",
            "--ssh-key-values", f"{ssh_key_path}.pub",
            "--location", location,
            "--output", "table"
        ]
        run_az_command(create_vm_cmd)
    else:
        print(f"VM {vm_name} already exists")
    
    # 4. Open Port 8081 Inbound
    print("=== 4. Opening NSG Port 8081 Inbound ===")
    create_nsg_cmd = [
        "az", "network", "nsg", "rule", "create",
        "--resource-group", rg_name,
        "--nsg-name", nsg_name,
        "--name", "Allow_8081_Inbound",
        "--priority", "1010",
        "--destination-port-ranges", port,
        "--direction", "Inbound",
        "--access", "Allow",
        "--protocol", "Tcp",
        "--description", "Allow FastAPI web traffic on port 8081",
        "--output", "table"
    ]
    run_az_command(create_nsg_cmd)

    # 5a. Retrieve public IP of the new VM and SCP bootstrap script to remote VM
    print("=== 5a. Retrieving Public IP of the VM ===")
    get_vm_public_ip_cmd = [
        "az", "vm", "list-ip-addresses",
        "-g", rg_name,
        "-n", vm_name,
        "--query", "[0].virtualMachine.network.publicIpAddresses[0].ipAddress",
        "-o", "tsv"
    ]
    vm_public_ip = run_az_command(get_vm_public_ip_cmd).strip().replace("\r", "")

    print(f"=== 5b. Copying Bootstrap Script to Remote VM ({vm_public_ip}) ===")
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-i", ssh_key_path,
        source_bootstrap_path,
        f"azureuser@{vm_public_ip}:~/"
    ]
    run_az_command(scp_cmd)

    # 6. SSH and run the remote bootstrap script to set up Docker, Docker Compose, and deploy the FastAPI application
    print("=== 6. SSH into VM and Execute Bootstrap Script ===")
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-i", ssh_key_path,
        f"azureuser@{vm_public_ip}",
        "sudo bash ~/bootstrap_vm.sh"
    ]
    run_az_command(ssh_cmd)


    print(f"Deployment Complete: API Endpoint - http://{vm_public_ip}:{port}")

    print("\n=== 9. How to End/Teardown VM (Cost Control) ===")
    
    # Interactive prompt
        # App display instruction/prompt
        # App display options

        # User input
        # App validate input

        # App execute action based on input
        # If option is another prompt, repeat the process
    print("To temporarily stop the VM and suspend compute billing (deallocate VM):")
    print(f"az vm deallocate --name {vm_name} --resource-group {rg_name} --no-wait")
    print("\nTo permanently delete the VM, disk, networks, and the resource group:")
    print(f"az group delete --name {rg_name} --no-wait --yes")

if __name__ == "__main__":
    main()