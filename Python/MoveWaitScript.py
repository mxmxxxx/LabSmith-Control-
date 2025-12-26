"""
MoveWait Script

This script demonstrates how to use the LabsmithBoard interface with MoveWait function.
"""

def main(app):
    """
    Example script for MoveWait functionality
    
    Args:
        app: The LabsmithBoard interface object
    """
    # Set flow rates for multiple pumps
    app.SetFlowRate('Pump_pH', 100, 'Pump_Na', 5, 'Pump_K', 100, 'Pump_aCSF', 5, 'Pump_Ca', 100)
    
    # Execute MoveWait command
    app.MoveWait(5, 'Pump_pH', 1, 'Pump_K', 1, 'Pump_Na', 1, 'Pump_aCSF', 1)
    
    # Alternative single pump example
    # app.MoveWait(3, 'Pump_pH', 10)

if __name__ == '__main__':
    # This would typically be called from another context where 'app' is an instance of LabsmithBoard
    print("This script is intended to be imported and used with a LabsmithBoard instance")
    print("Example usage:")
    print("  from LabsmithBoard import LabsmithBoard")
    print("  app = LabsmithBoard(port)")
    print("  from MoveWaitScript import main")
    print("  main(app)")




