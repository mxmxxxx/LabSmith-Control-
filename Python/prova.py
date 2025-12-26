"""
Prova Script

This script demonstrates various operations with the LabsmithBoard interface.
Contains multiple commented out examples and active test code.
"""

def main(app):
    """
    Example script for testing various LabsmithBoard operations
    
    Args:
        app: The LabsmithBoard interface object
    """
    # Various commented out examples:
    # SetFlowRate(app.LI, 'Pump_pH', 100, 'Pump_Na', 100, 'Pump_K', 100, 'Pump_aCSF', 100, 'Pump_Ca', 100)
    # MulMove2(app.LI, 'Pump_pH', 10, 'Pump_aCSF', 10, 'Pump_K', 10, 'Pump_Na', 10, 'Pump_Ca', 10)
    # MulMove2(app.LI, 'Pump_pH', 1, 'Pump_aCSF', 1, 'Pump_K', 1, 'Pump_Na', 1, 'Pump_Ca', 1)
    # a = 1
    # SetValves(app.LI, 'Manifold1', a, a, a, a)
    # SetValves(app.LI, 'Manifold2', a, a, a, a)
    # a = 3
    # SetValves(app.LI, 'Manifold1', a, a, a, a)
    # SetValves(app.LI, 'Manifold2', a, a, a, a)
    
    # a = 3
    # SetValves2(app.LI, 'Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    # a = 1
    # SetValves2(app.LI, 'Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    
    # SetFlowRate(app.LI, 'Pump_pH', 100, 'Pump_Na', 5, 'Pump_K', 100, 'Pump_aCSF', 5, 'Pump_Ca', 100)
    # MoveWait(app.LI, 5, 'Pump_pH', 1, 'Pump_K', 1, 'Pump_Na', 1, 'Pump_aCSF', 1)
    # MulMove3(app.LI, 'Pump_pH', 5)
    
    # a = 3
    # SetValves(app.LI, 'Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    
    # MulMove3(app.LI, 'Pump_pH', 1)
    
    # a = 10
    # MulMove3(app.LI, 'Pump_K', a, 'Pump_pH', a, 'Pump_aCSF', a, 'Pump_Na', a)
    # MulMove3(app.LI, 'Pump_K', 3, 'Pump_pH', 6, 'Pump_aCSF', 9, 'Pump_Na', 12, 'Pump_Ca', 15)
    # MulMove3(app.LI, 'Pump_K', 10, 'Pump_pH', 10)
    
    # Active test code:
    a = 3
    app.SetValves2('Manifold1', a, a, a, a)
    app.MulMove3('Pump_pH', 8)
    
    a = 1
    app.SetValves2('Manifold1', a, a, a, a)
    app.MulMove3('Pump_pH', 1)
    
    # Additional commented examples:
    # a = 3
    # app.SetValves2('Manifold1', a, a, a, a)
    # app.MulMove3('Pump_pH', 3)
    # a = 1
    # app.SetValves2('Manifold1', a, a, a, a)
    # app.MulMove3('Pump_pH', 1)

if __name__ == '__main__':
    # This would typically be called from another context where 'app' is an instance of LabsmithBoard
    print("This script is intended to be imported and used with a LabsmithBoard instance")
    print("Example usage:")
    print("  from LabsmithBoard import LabsmithBoard")
    print("  app = LabsmithBoard(port)")
    print("  from prova import main")
    print("  main(app)")




