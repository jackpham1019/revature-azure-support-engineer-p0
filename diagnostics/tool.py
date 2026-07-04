import time
import ipaddress
from statistics import mean
from util import run_command
from datetime import datetime

CPU_WARNING = 70
CPU_CRITICAL = 90

MEMORY_WARNING = 70
MEMORY_CRITICAL = 90

DISK_WARNING = 80
DISK_CRITICAL = 90

EXPOSURE_PUBLIC = "PUBLIC"
EXPOSURE_INTERNAL = "INTERNAL"
EXPOSURE_LOCALHOST = "LOCALHOST"

COL_PROTOCOL = 8
COL_HOST = 20
COL_PORT = 8
COL_SERVICE = 25

cpu_sample_window = 1

def get_current_time():
    # Current local date and time
    now = datetime.now() # Example: 2026-07-04 09:58:00.123456

    # Formatted version (YYYY-MM-DD HH:MM:SS)
    return now.strftime("%Y-%m-%d %H:%M:%S")

def get_status(value, warning, critical):
    if value >= critical:
        return "CRITICAL"
    elif value >= warning:
        return "WARNING"
    else:
        return "NORMAL"

def check_cpu():
    print("=======================")
    print("Checking CPU usage...")

    cpu_command = ["vmstat", "1", "2"]
    cpu_command_output = run_command(cpu_command).splitlines()

    cpu_command_headers = cpu_command_output[1].split()
    cpu_command_values = cpu_command_output[-1].split()

    idle_index = cpu_command_headers.index("id")
    cpu_idle = float(cpu_command_values[idle_index])
    cpu_usage = 100 - cpu_idle

    print(f"CPU Usage: {cpu_usage:.2f}%")
    return cpu_usage

def check_memory():
    print("=======================")
    print("Checking memory usage...")

    memory_command = ["free", "-m"]
    memory_command_output = run_command(memory_command).splitlines()[1]

    values = memory_command_output.split()
    memory_total = float(values[1])
    memory_used = float(values[2])

    memory_used_percent = (memory_used / memory_total) * 100

    print(f"Memory Usage: {memory_used_percent:.2f}%")
    return memory_used_percent

def check_disk():
    print("=======================")
    print("Checking disk storage...")

    disk_command = ["df", "-m", "/"]
    disk_output = run_command(disk_command).splitlines()[1]

    values = disk_output.split()
    disk_total = float(values[1])
    disk_used = float(values[2])
    disk_available = float(values[3])

    disk_used_percent = (disk_used / disk_total) * 100

    print(f"Disk Usage: {disk_used_percent:.2f}%")

    return {
        "used_percent": disk_used_percent,
        "available_mb": disk_available
}

def check_listening_ports():
    print("=======================")
    print("Checking listening ports...")

    ports_command = ["ss", "-tulpn"]
    listening_ports = []

    for line in run_command(ports_command).splitlines()[1:]:
        parts = line.split()

        if len(parts) < 5:
            continue

        protocol = parts[0]
        local_address = parts[4]

        print(local_address)
        # Handles examples like:
        # 127.0.0.1:8000
        # 0.0.0.0:80
        # [::]:443
        # [::1]:323
        # 127.0.0.53%lo:53
        if local_address.startswith("["):
            host, port = local_address[1:].rsplit("]:", 1)
        else:
            host, port = local_address.rsplit(":", 1)

        host = host.split("%")[0]

        listening_ports.append(
            {
                "port": port,
                "host": host,
                "protocol": protocol,
            }
        )

    return listening_ports


def perform_diagnostics():
    cpu = check_cpu()
    memory = check_memory()
    disk = check_disk()
    listening_ports = check_listening_ports()

    return {
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "listening_ports": listening_ports,
    }


def collect_metrics(period: int = 5, interval: int = 1):
    metrics = {
        "cpu": [],
        "memory": [],
        "disk": None,
        "listening_ports": [],
    }

    start_time = get_current_time()

    for _ in range(period // interval):
        diagnostics = perform_diagnostics()

        metrics["memory"].append(diagnostics["memory"])
        metrics["cpu"].append(diagnostics["cpu"])

        time.sleep(max(0, interval-cpu_sample_window))

    metrics["disk"] = diagnostics["disk"]
    metrics["listening_ports"] = diagnostics["listening_ports"]

    end_time = get_current_time()

    return {
        "period": dict(
            start_time=start_time,
            end_time=end_time,
            interval=interval
        ),
        "metrics": metrics
    }

def get_exposure(host):

    if host in ("0.0.0.0", "::", "*"):
        return EXPOSURE_PUBLIC

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "UNKNOWN"

    if ip.is_loopback:
        return EXPOSURE_LOCALHOST

    if ip.is_private:
        return EXPOSURE_INTERNAL

    return EXPOSURE_PUBLIC

def get_service(port):
    KNOWN_PORTS = {
        # Infrastructure & Networking
        "22": "SSH",
        "53": "DNS",
        "67": "DHCP Server",
        "68": "DHCP Client",
        "123": "NTP",
        "323": "Chronyd",

        # Web
        "80": "HTTP",
        "443": "HTTPS",
        "8080": "HTTP Alternate",
        "8443": "HTTPS Alternate",

        # Databases & Caching
        "1433": "SQL Server",
        "1521": "Oracle",
        "3306": "MySQL",
        "5432": "PostgreSQL",
        "6379": "Redis",
        "27017": "MongoDB",

        # Remote Access
        "3389": "RDP",
        "5900": "VNC",

        # Messaging & Streaming
        "5672": "RabbitMQ",
        "9092": "Kafka",

        # Monitoring & Observability
        "3000": "Grafana",
        "9090": "Prometheus",

        # Containers & Orchestration
        "2375": "Docker API (Unsafe)",
        "2376": "Docker API (TLS)",
        "6443": "Kubernetes API Server",

        # Email
        "25": "SMTP",
        "587": "SMTP Submission",
        "993": "IMAPS",
        "995": "POP3S",
    }

    if port in KNOWN_PORTS:
        return KNOWN_PORTS[port]
    return "UNKNOWN"

def analyze_metrics(metrics):
    cpu_average = mean(metrics["metrics"]["cpu"])
    cpu_peak = max(metrics["metrics"]["cpu"])

    memory_average = mean(metrics["metrics"]["memory"])
    memory_peak = max(metrics["metrics"]["memory"])

    disk = metrics["metrics"]["disk"]
    listening_ports = metrics["metrics"]["listening_ports"]
    analyzed_ports_by_exposure = {
        EXPOSURE_INTERNAL: [],
        EXPOSURE_LOCALHOST: [],
        EXPOSURE_PUBLIC: []
    }

    for entry in listening_ports:
        
        host = entry["host"]
        port = entry["port"]
        exposure = get_exposure(host)
        service = get_service(port)
        protocol = entry["protocol"]

        analyzed_ports_by_exposure[exposure].append(dict(
            host=host,
            service=service,
            protocol=protocol,
            port=port
        ))

    return {
        "period": metrics["period"],
        "cpu": {
            "average_used_percent": cpu_average,
            "max_used_percent": cpu_peak,
            "status": get_status(cpu_peak, CPU_WARNING, CPU_CRITICAL),
        },
        "memory": {
            "average_used_percent": memory_average,
            "max_used_percent": memory_peak,
            "status": get_status(memory_peak, MEMORY_WARNING, MEMORY_CRITICAL),
        },
        "disk": {
            "used_percent": disk["used_percent"],
            "available_mb": disk["available_mb"],
            "status": get_status(disk["used_percent"], DISK_WARNING, DISK_CRITICAL),
        },
        "listening_ports_by_exposure": analyzed_ports_by_exposure,
    }

def generate_report(report):

    lines = []

    lines.append("=" * 50)
    lines.append("SYSTEM DIAGNOSTIC REPORT")
    lines.append("=" * 50)

    lines.append(f"Start Time: {report['period']['start_time']}")
    lines.append(f"End Time: {report['period']['end_time']}")
    lines.append(f"Interval: {report['period']['interval']}s")

    # CPU
    lines.append("")
    lines.append("CPU")
    lines.append("-" * 20)
    lines.append(
        f"Average Usage : {report['cpu']['average_used_percent']:.2f}%"
    )
    lines.append(
        f"Peak Usage    : {report['cpu']['max_used_percent']:.2f}%"
    )
    lines.append(
        f"Status        : {report['cpu']['status']}"
    )

    # Memory
    lines.append("")
    lines.append("Memory")
    lines.append("-" * 20)
    lines.append(
        f"Average Usage : {report['memory']['average_used_percent']:.2f}%"
    )
    lines.append(
        f"Peak Usage    : {report['memory']['max_used_percent']:.2f}%"
    )
    lines.append(
        f"Status        : {report['memory']['status']}"
    )

    # Disk
    lines.append("")
    lines.append("Disk")
    lines.append("-" * 20)
    lines.append(
        f"Usage         : {report['disk']['used_percent']:.2f}%"
    )
    lines.append(
        f"Available     : {report['disk']['available_mb']:.0f} MB"
    )
    lines.append(
        f"Status        : {report['disk']['status']}"
    )

    # Listening Ports
    lines.append("")
    lines.append("Listening Ports")
    lines.append("-" * 20)

    listening_ports_by_exposure = report["listening_ports_by_exposure"]

    for exposure, ports in listening_ports_by_exposure.items():
        lines.append("")
        lines.append("-" * 10)
        lines.append(exposure)
        lines.append("-" * 10)

        lines.append(
            f"{'Protocol':<{COL_PROTOCOL}} "
            f"{'Host':<{COL_HOST}} "
            f"{'Port':<{COL_PORT}} "
            f"{'Service':<{COL_SERVICE}}"
        )

        lines.append(
            f"{'-' * COL_PROTOCOL} "
            f"{'-' * COL_HOST} "
            f"{'-' * COL_PORT} "
            f"{'-' * COL_SERVICE}"
        )

        for port in ports:
            lines.append(
                f"{port['protocol']:<{COL_PROTOCOL}} "
                f"{port['host']:<{COL_HOST}} "
                f"{port['port']:<{COL_PORT}} "
                f"{port['service']:<{COL_SERVICE}}"
            )

    lines.append("")
    lines.append("=" * 50)

    return "\n".join(lines)

def run_analysis_and_get_report(period=5, interval=1):
    metrics = collect_metrics(period=5, interval=1)
    analysis = analyze_metrics(metrics)
    report = generate_report(analysis)
    return report

if __name__ == "__main__":
    metrics = collect_metrics(period=5, interval=1)
    analysis = analyze_metrics(metrics)
    report = generate_report(analysis)
    print(report)