"""
MoveWait Script

Example showing how to drive multi-pump moves through LabsmithBoard.MoveWait().

Prerequisites:
- A LabsmithBoard instance connected to at least 4 SPS01 pumps.
- Pump names passed in (`Pump_pH`, `Pump_Na`, `Pump_K`, `Pump_aCSF`, `Pump_Ca`)
  must match `GetName()` on the actually-connected syringes. Adjust the strings
  to match the customer's hardware. If fewer than 4 pumps are connected, reduce
  the MoveWait call to the matching pump count (signature accepts 1..4 pumps).

MoveWait(time, d1, v1, d2, v2, ...) starts all named pumps toward their target
volumes, then waits up to `time` seconds for completion. It supports Stop / Pause
/ Resume via `LabsmithBoard.Stop`, `.Pause`, `.Resume` flags.
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




