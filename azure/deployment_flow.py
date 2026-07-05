import os
import time
import requests

from textwrap import dedent
from dotenv import load_dotenv
from cli.prompt import InteractivePrompt
from cli.manager import PromptManager
from cli.option import PromptOption
from util import run_command

load_dotenv()

def send_discord_notification(username, message):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    payload = {
        "username": username,
        "content": message
    }

    response = requests.post(
        webhook_url,
        json=payload,
        timeout=10
    )

    response.raise_for_status()
    
def prompt_for_teardown(rg_name, vm_name):
    
    deallocate_cmd = ["az", "vm", "deallocate", "--name", vm_name, "--resource-group", rg_name]
    delete_cmd = ["az", "group", "delete", "--name", rg_name, "--yes"]

    prompt = InteractivePrompt(
        "How would you like to end the VM? (Enter 0 to exit prompt)",
        [
            PromptOption(
                "Temporarily stop the VM and suspend compute billing (deallocate VM)", 
                InteractivePrompt(
                    "Would you like to wait for the deallocation to complete?",
                    [
                        PromptOption(
                            "Yes", 
                            deallocate_cmd, 
                            exit_after=True),
                        PromptOption(
                            "No",
                            [
                                *deallocate_cmd, 
                                "--no-wait"
                            ], 
                            exit_after=True)
                    ]
                )
            ),
                                  
              
            PromptOption(
                "Permanently delete the VM, disk, networks, and the resource group", 
                InteractivePrompt(
                    "Would you like to wait for the deletion to complete?", 
                    [
                        PromptOption(
                            "Yes",
                            delete_cmd, 
                            exit_after=True),
                        PromptOption(
                            "No", 
                            [
                                *delete_cmd, 
                                "--no-wait"
                            ],
                            exit_after=True)
                    ]
                )
            )
        ]
    )

    prompt_manager = PromptManager(prompt_stack=[prompt])
    prompt_manager.run()

def main():

    deployment_start_time = time.perf_counter()

    print("=== Azure SRE DOcker Compose Automated Deployment Pipeline using Python ===")

    # 1. Capture user inputs
    rg_name = input("Enter Resource Group [rg-project-0]: ").strip() or "rg-project-0"
    vm_name = input("Enter VM Name [vm-appserver-project-0]: ").strip() or "vm-appserver-project-0"
    location = input("Enter Region [canadaeast]: ").strip() or "canadaeast"

    nsg_name = f"{vm_name}-NSG"

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
        run_command(generate_ssh_key_cm)
    else:
        print(f"SSH key already exists: {ssh_key_path}")

    print(f"\nConfiguration:")
    print(f"- Resource Group: {rg_name}")
    print(f"- VM Name: {vm_name}")
    print(f"- Location: {location}")
    print(f"- Exposed Port: {port}\n")
    print()

    # 2. Create Resource Group
    print("=== 2. Ensuring Resource Group Exists ===")
    create_rg_cmd = ["az", "group", "create", "--name", rg_name, "--location", location, "--output", "table"]
    run_command(create_rg_cmd)

    # 3a. Check and create VM if not exists
    check_vm_cmd = ["az", "vm", "list", "-g", rg_name, "--query", f"[?name=='{vm_name}'].name", "-o", "tsv"]
    vm_check_output = run_command(check_vm_cmd).strip()

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
        run_command(create_vm_cmd)

    # 3b. Retrieve public IP of the VM
    print("=== 3b. Retrieving Public IP of the VM ===")
    get_vm_public_ip_cmd = [
        "az", "vm", "list-ip-addresses",
        "-g", rg_name,
        "-n", vm_name,
        "--query", "[0].virtualMachine.network.publicIpAddresses[0].ipAddress",
        "-o", "tsv"
    ]
    vm_public_ip = run_command(get_vm_public_ip_cmd).strip().replace("\r", "")
    print()

    # 3. If VM already exists, send skipped notification to Discord, and prompt for teardown operations
    if vm_check_output:
        print(f"VM {vm_name} already exists")
    
        # 3c. Sending deployment skipped notification to Discord
        print("\n=== 3c. Sending deployment skipped notification to Discord ===")
        send_discord_notification(
            "Python Automation Script",
            dedent(f"""
                VM {vm_name} already exists
                
                Public IP - http://{vm_public_ip}
            """)
        )
        print()
        prompt_for_teardown(rg_name, vm_name)
        return
        
    vm_provision_time = time.perf_counter() - deployment_start_time

    # 3d. Configure Auto-Shutdown schedule
    shutdown_time = "2100"
    auto_shutdown_cmd = [
        "az", "vm", "auto-shutdown", 
        "-g", rg_name, 
        "-n", vm_name, 
        "--time", shutdown_time,
        "-o", "none"]
    run_command(auto_shutdown_cmd)

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
    run_command(create_nsg_cmd)
    print()
        
    # 5. Sending deployment successful notification to Discord
    print("\n=== 5b. Sending deployment successful notification to Discord ===")
    send_discord_notification(
        "Python Automation Script",
        dedent(f"""
            VM Provisioned successfully
            
            Resource Group: {rg_name}
            VM Name: {vm_name}
            Public IP - http://{vm_public_ip}
            
            Deployment time: {vm_provision_time//3600:.0f}h {((vm_provision_time% 3600) //60):.0f}m {vm_provision_time%60:.0f}s

            Auto-Shutdown: VM is configured to shut down daily at 5PM EDT
        """)
    )
    print()
    
    bootstrap_start_time = time.perf_counter()

    # 6. SCP bootstrap script to remote VM
    print(f"=== 6. Copying Bootstrap Script to Remote VM ({vm_public_ip}) ===")
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-i", ssh_key_path,
        source_bootstrap_path,
        f"azureuser@{vm_public_ip}:~/"
    ]
    run_command(scp_cmd)
    print()

    # 7a. SSH and run the remote bootstrap script to set up Docker, Docker Compose, and deploy the FastAPI application
    print("=== 7a. SSH into VM and Execute Bootstrap Script ===")
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-i", ssh_key_path,
        f"azureuser@{vm_public_ip}",
        "sudo bash ~/bootstrap_vm.sh"
    ]
    run_command(ssh_cmd, print_result=False)
    print()

    bootstrap_time = time.perf_counter() - bootstrap_start_time

    # 7b. Send bootstrapping completion notification to Discord
    print("\n=== 7b. Sending notification to Discord ===")
    send_discord_notification(
        "Python Automation Script",
        dedent(f"""
            VM bootstrapped successfully
            Demo application is ready
               
            VM Name: {vm_name}

            API Endpoint - http://{vm_public_ip}:{port}
            Health check: http://{vm_public_ip}:{port}/health
            DB check: http://{vm_public_ip}:{port}/db-check
            
            VM bootstrap time: {bootstrap_time//3600:.0f}h {((bootstrap_time% 3600) //60):.0f}m {bootstrap_time%60:.0f}s
        """)
    )
    print()


    elapsed_time = time.perf_counter() - deployment_start_time
    print(f"Total Deployment & Bootstrap Time: {elapsed_time:.2f} seconds")
    print()

    print("\n=== 8. How to End/Teardown VM (Cost Control) ===")
    prompt_for_teardown(rg_name, vm_name)

def start_deployment():
    try:
        main()
    except Exception as e:
        send_discord_notification(
            f"Azure VM",
            dedent(f"""
            ❌ Deployment Failed

            Error: {type(e).__name__}
            Message: {e}     
            """)
        )
        raise

if __name__ == "__main__":
    start_deployment()