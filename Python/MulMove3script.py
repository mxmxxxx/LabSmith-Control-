"""
MulMove3 Script

This script demonstrates how to use the LabsmithBoard interface with MulMove3 function.
"""

def main(app):
    """
    Example script for MulMove3 functionality
    
    Args:
        app: The LabsmithBoard interface object
    """
    # Set flow rates for multiple pumps
    app.SetFlowRate('Pump_pH', 100, 'Pump_Na', 100, 'Pump_K', 100, 'Pump_aCSF', 100, 'Pump_Ca', 100)
    
    # Execute MulMove3 command with multiple pumps
    a = 1
    app.MulMove3('Pump_pH', a, 'Pump_Na', a)
    
    # Alternative multi-pump example
    # a = 1
    # app.MulMove3('Pump_K', a, 'Pump_pH', a, 'Pump_aCSF', a, 'Pump_Na', a)

if __name__ == '__main__':
    # This would typically be called from another context where 'app' is an instance of LabsmithBoard
    print("This script is intended to be imported and used with a LabsmithBoard instance")
    print("Example usage:")
    print("  from LabsmithBoard import LabsmithBoard")
    print("  app = LabsmithBoard(port)")
    print("  from MulMove3script import main")
    print("  main(app)")




