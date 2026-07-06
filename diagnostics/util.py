
from datetime import datetime
from pathlib import Path

desktop = Path("/mnt/c/Users/Quang Pham/OneDrive/Desktop")

def save_report(name, report):
    """
    Save the generated report to a file.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.txt"

    with open(desktop / filename, "w") as file:
        file.write(report)
