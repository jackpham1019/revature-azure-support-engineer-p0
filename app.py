"""

"""
from datetime import datetime 
import subprocess
import sys
from azure_flow import main as azure_flow_main

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

def perform_diagnostics():
    """
    Perform system diagnostics and return the results.
    """

    """
    Questions to answer:
        Is the CPU usage high?
        Is the memory usage high?
        Are there available disk space?
        Are important services running?
        Are applications listening on the expected ports?
        Is the system overloaded or recovering?
        Has the machine been stable?
    """


    print("=======================")
    print("Checking CPU usage...")
    cpu_command = ["vmstat", "1", "2"]
    cpu_command_output = run_linux_command(cpu_command).splitlines()
    cpu_command_headers = cpu_command_output[1].split()
    cpu_command_values = cpu_command_output[-1].split()

    idle_index = cpu_command_headers.index("id")
    cpu_idle = cpu_command_values[idle_index]
    cpu_usage = 100 - float(cpu_idle)

    cpu_top_processes_command = ["ps", "-eo", "pid,ppid,comm,%mem,%cpu", "--sort=-%cpu", "--no-headers"]
    cpu_top_processes_output = run_linux_command(cpu_top_processes_command).splitlines()
    cpu_top_processes = []
    for process in cpu_top_processes_output[:5]:
        pid, ppid, comm, mem, cpu = process.split(None, 4)
        cpu_top_processes.append({
            "pid": pid,
            "ppid": ppid,
            "comm": comm,
            "mem": float(mem),
            "cpu": float(cpu)
        })

    if cpu_usage < 70:
        cpu_status = "NORMAL"
    elif cpu_usage < 90:
        cpu_status = "WARNING"
    else:
        cpu_status = "HIGH"


    print("=======================")
    print("Checking memory usage...")
    memory_command = ["free", "-m"]
    memory_command_output = run_linux_command(memory_command).splitlines()[1]

    memory_total = float(memory_command_output.split()[1])
    memory_used = float(memory_command_output.split()[2])
    memory_available = float(memory_command_output.split()[6])
    memory_used_percent = (memory_used / memory_total) * 100
    available_percent = (memory_available / memory_total) * 100

    if memory_used_percent < 70:
        memory_status = "NORMAL"
    elif memory_used_percent < 90:
        memory_status = "WARNING"
    else:
        memory_status = "HIGH"


    print("=======================")
    print("Checking disk storage")
    disk_command = ["df", "-m", "/"]
    disk_output = run_linux_command(disk_command).splitlines()[1]

    disk_total = float(disk_output.split()[1])
    disk_available = float(disk_output.split()[3])
    disk_used = float(disk_output.split()[2])
    disk_used_percent = disk_used / disk_total * 100
    
    if disk_used_percent < 80:
        disk_status = "NORMAL"
    elif disk_used_percent < 90:
        disk_status = "WARNING"
    else:
        disk_status = "CRITICAL"


    print("=======================")
    print("Checking listening ports...")
    ports_command = ["ss", "-tulpn"]
    application_services = []
    SYSTEM_PORTS = ["53", "323"]
    for line in run_linux_command(ports_command).splitlines()[1:]:
        curLine = line.split()
        curPort = curLine[4].split(":")[-1]
        if curPort in SYSTEM_PORTS:
            pass
        else:
            process_info = curLine[6].split(":")[-1][2:-2].split(",")
            application_services.append(
                {
                    "process_name": process_info[0].replace('"', ''), 
                    "pid": process_info[1].split("=")[-1],
                    "port": int(curPort)
                }
            ) 

    return {
        "cpu": {
            "total_usage": float(cpu_usage),
            "top_processes": cpu_top_processes,
            "status": cpu_status
        },
        "memory": {
            "total": float(memory_total),
            "used": float(memory_used),
            "available": float(memory_available),
            "available_percent": memory_available / memory_total * 100,
            "used_percent": memory_used_percent,
            "status": memory_status
        },
        "disk": {
            "total": float(disk_total),
            "used": float(disk_used),
            "available": float(disk_available),
            "used_percent": disk_used_percent,
            "available_percent": disk_available / disk_total * 100,
            "status": disk_status
        },
        "application_services": application_services,
        # "system_overloaded": False,
        # "machine_stable": True,
    }

def generate_report(diagnostics):
    """
    Generate a report based on the diagnostic results.
    """

    lines = []
    cpu = diagnostics['cpu']
    memory = diagnostics['memory']
    disk = diagnostics['disk']
    application_services = diagnostics['application_services']

    lines.append("==============================")
    lines.append("Local Linux Health Diagnostics")
    lines.append("==============================")
    lines.append("")


    lines.append("---")
    lines.append("CPU")
    lines.append("---")
    lines.append(f"Total usage: {cpu['total_usage']:.2f}%")
    lines.append("Top running processes:")
    for process in cpu['top_processes']:
        lines.append(f"- {process['comm']}, pid: {process['pid']}, cpu: {process['cpu']}%, mem: {process['mem']}")
    lines.append("")
    lines.append(f"Status: {cpu['status']}")
    lines.append("")


    lines.append("------")
    lines.append("Memory")
    lines.append("------")
    lines.append(f"Available: {memory['available']}MiB/{memory['total']}MiB ({memory['available_percent']:.2f}%)")
    lines.append("")
    lines.append(f"Status: {memory['status']}")
    lines.append("")
    
    
    lines.append("----")
    lines.append("Disk")
    lines.append("----")
    lines.append(f"Available: {disk['available']}MB/{disk['total']}MB ({disk['available_percent']:.2f}%)")
    lines.append("")
    lines.append(f"Status: {disk['status']}")
    lines.append("")


    lines.append("--------------------")
    lines.append("Application Services")
    lines.append("--------------------")    
    lines.append("")

    for app in application_services:
        lines.append(f"{app['process_name']}, pid: {app['pid']}, port: {app['port']}")

    lines.append("")
    return "\n".join(lines)

def print_report(report):
    """
    Print the generated report to the console.
    """
    print("")
    print("/// PRINTING REPORT TO TERMINAL ///")
    print("")
    print(report)

def save_report(report):
    """
    Save the generated report to a file.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"linux_diagnostics_{timestamp}.txt"

    with open(filename, "w") as file:
        file.write(report)

def get_formatted_report():
    diagnostics = perform_diagnostics()
    return generate_report(diagnostics)

if __name__ == "__main__":
    # SCRIPT PROCEDURE
    # Perform diagnostics
    # Ask for permission to start deployment
    # START of deployment process
        # Authenticate & provision resources via Azure CLI
        # Deploy to Standard_B1s VM + HDD
        # Configure auto-shutdown schedule
        # Print command for manual exit

    report = get_formatted_report()

    user_decision = input("Do you want to deploy the tool to Azure? (y/n) [n]: ").strip().lower()
    valid_decisions = ["y", "n", "", "yes", "no"]

    while user_decision not in valid_decisions:
        user_decision = input("Invalid input. Please enter 'y' or 'n' [n]: ").strip().lower()
    
    if user_decision in ["y", "yes"]:
        # START of deployment process
        print("Starting deployment process...")
        azure_flow_main()
        pass
    else:
        print_report(report)
        save_report(report)
        print("Report saved successfully.")
