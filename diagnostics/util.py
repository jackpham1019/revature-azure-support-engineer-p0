
from datetime import datetime

def save_report(name, report):
    """
    Save the generated report to a file.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.txt"

    with open(filename, "w") as file:
        file.write(report)
