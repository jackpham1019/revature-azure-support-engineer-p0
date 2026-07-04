"""
    Linux Health Diagnostics Tool
"""

from azure.deployment_flow import main as azure_flow_main
from diagnostics.tool import run_analysis_and_get_report
from diagnostics.util import save_report

if __name__ == "__main__":
    # SCRIPT PROCEDURE
    # Perform diagnostics
    # Ask for permission to start deployment
    # START of deployment process
        # Authenticate & provision resources via Azure CLI
        # Deploy to Standard_B1s VM + HDD
        # Configure auto-shutdown schedule
        # Print command for manual exit

    report = run_analysis_and_get_report()

    user_decision = input("Do you want to deploy the tool to Azure? (y/n) [n]: ").strip().lower()
    valid_decisions = ["y", "n", "", "yes", "no"]

    while user_decision not in valid_decisions:
        user_decision = input("Invalid input. Please enter 'y' or 'n' [n]: ").strip().lower()
    
    if user_decision in ["y", "yes"]:
        # START of deployment process
        print("Starting deployment process...")
        azure_flow_main()

    else:
        print(report)
        save_report(report)
        print("Report saved successfully.")
