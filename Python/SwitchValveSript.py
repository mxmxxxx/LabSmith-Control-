"""
SwitchValve Script

This script demonstrates how to use the LabsmithBoard interface with valve switching functions.
"""

def main(app):
    """
    Example script for switching valves in manifolds
    
    Args:
        app: The LabsmithBoard interface object
    """
    # Example valve switching for multiple manifolds
    a = 3
    app.SetValves2('Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    
    a = 1
    app.SetValves2('Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    
    # Alternative example with iteration (commented out)
    # for i in range(1, 11):
    #     comment = f'iteration {i}'
    #     print(comment)
    #     a = 3
    #     app.SetValves2('Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    #     a = 2
    #     app.SetValves2('Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    #     a = 1
    #     app.SetValves2('Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)
    #     a = 2
    #     app.SetValves2('Manifold1', a, a, a, a, 'Manifold2', a, a, a, a)

if __name__ == '__main__':
    # This would typically be called from another context where 'app' is an instance of LabsmithBoard
    print("This script is intended to be imported and used with a LabsmithBoard instance")
    print("Example usage:")
    print("  from LabsmithBoard import LabsmithBoard")
    print("  app = LabsmithBoard(port)")
    print("  from SwitchValveSript import main")
    print("  main(app)")




