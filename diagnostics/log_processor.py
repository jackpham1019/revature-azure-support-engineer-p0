"""

"""

def parse_log_line(line):
    """
    Parses a single log line in Common Log Format.
    Example line:
    192.168.1.15 - - [10/Jun/2026:10:15:35 +0000] "POST /api/v1/login HTTP/1.1" 401 12 95

    Returns a dictionary of parsed parts:
    {
        "ip": "192.168.1.15",
        "method": "POST",
        "path": "/api/v1/login",
        "status": 401,
        "latency": 95
    }
    """
    try:
        parts = line.strip().split()
        if len(parts) < 11:
            return None
        
        ip = parts[0]
        method = parts[5].replace('"', '')
        path = parts[6]
        status = int(parts[8])
        latency = int(parts[10])
        
        return {
            "ip": ip,
            "method": method,
            "path": path,
            "status": status,
            "latency": latency
        }
    except Exception as e:
        print(f"Error parsing line: {line}. Detail: {e}")
        return None
def analyze_by_path(requests):
    req_by_path = {}
    slow_paths = []
    critical_paths = []

    for req in requests:
        path = req["path"]
        status = req["status"]
        latency = req["latency"]

        if path not in req_by_path:
            req_by_path[path] = {
                "error": 0,
                "slow_response": 0
            }

        if status == 500:
            req_by_path[path]["error"] += 1

        if latency > 100:
            req_by_path[path]["slow_response"] += 1

    for path, data in req_by_path.items():
        if data["error"] >= 3:
            critical_paths.append({
                "path": path,
                "num_of_error": data["error"]
            })

        if data["slow_response"] >= 3:
            slow_paths.append({
                "path": path,
                "num_of_slow": data["slow_response"]
            })

    return {
        "slow_paths": slow_paths,
        "critical_paths": critical_paths
    }

def analyze_logs(file_path):
    """
    Reads the logs file, parses each line, and aggregates metrics using lists, sets, and dicts.
    """

    print(f"=== Analyzing logs from : {file_path} ===")

    all_requests = []
    unique_ips = set()
    status_counts = {}
    slow_requests = []
    request_by_ip = {}

    with open(file_path, 'r') as file:
        for line in file:
            parsed_line = parse_log_line(line)
            if not parsed_line:
                continue

            all_requests.append(parsed_line)
            # ip = ipaddress.ip_address(parsed_line["ip"])
            ip = parsed_line["ip"]

            request_by_ip.setdefault(ip, []).append({
                "method": parsed_line["method"],
                "path": parsed_line["path"],
                "status": parsed_line["status"],
                "latency": parsed_line["latency"]
            })
            
            unique_ips.add(ip)

            status = parsed_line["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

            if parsed_line["latency"] > 100:
                slow_requests.append(parsed_line)
    
    return dict(
        all_requests=all_requests,
        unique_ips=unique_ips,
        status_counts=status_counts,
        slow_requests=slow_requests,
        analysis_by_path=analyze_by_path(all_requests)
    )

def generate_log_report(analysis_result):
    all_requests = analysis_result["all_requests"]
    unique_ips = analysis_result["unique_ips"]
    status_counts = analysis_result["status_counts"]
    slow_requests = analysis_result["slow_requests"]
    analysis_by_path = analysis_result["analysis_by_path"]
    
    lines = []

    lines.append("=" * 41)
    lines.append("SRE LOG ANALYSIS SUMMARY REPORT")
    lines.append("=" * 41)

    lines.append(f"Total Requests Processed: {len(all_requests)}")
    lines.append(f"Unique Client IPs: {len(unique_ips)}")
    lines.append(f"HTTP Status Code Breakdown: {status_counts}")
    lines.append(f"Slow Requests (>100ms) Count: {len(slow_requests)}")

    lines.append("-" * 41)

    # Unique IPs
    lines.append("Detailed List of Unique Client IPs:")
    for ip in sorted(unique_ips):
        lines.append(f"  {ip}")

    # Slow requests
    lines.append("")
    lines.append("Detailed List of Slow Requests:")
    if slow_requests:
        for req in slow_requests:
            lines.append(
                f"  {req['method']:6} "
                f"{req['path']:25} "
                f"Latency: {req['latency']:4}ms "
                f"Status: {req['status']}"
            )
    else:
        lines.append("  None")

    # Critical paths
    lines.append("")
    lines.append("Paths with Multiple 500 Errors:")
    if analysis_by_path["critical_paths"]:
        for req in analysis_by_path["critical_paths"]:
            lines.append(
                f"  {req['path']:25} "
                f"Errors: {req['num_of_error']}"
            )
    else:
        lines.append("  None")

    # Slow paths
    lines.append("")
    lines.append("Slow Paths:")
    if analysis_by_path["slow_paths"]:
        for req in analysis_by_path["slow_paths"]:
            lines.append(
                f"  {req['path']:25} "
                f"Slow Requests: {req['num_of_slow']}"
            )
    else:
        lines.append("  None")

    return "\n".join(lines)

def run_analysis_and_get_report(file_path):
    analysis_result = analyze_logs(file_path)
    return generate_log_report(analysis_result)

if __name__ == "__main__":
    import os
    # Find logs.txt relative to this script
    logs_file = os.path.join(os.path.dirname(__file__), "sample_logs.txt")
    if os.path.exists(logs_file):
        analyze_logs(logs_file)
    else:
        print(f"Error: {logs_file} not found. Please run this script in its local folder.")

