"""
Example Calculator Module
A simple calculator with various operations
"""

import math
from typing import List


# Global configuration
DEBUG_MODE = True
PI = 3.14159


def add(a: float, b: float) -> float:
    """Add two numbers"""
    result = a + b
    if DEBUG_MODE:
        print(f"Adding {a} + {b} = {result}")
    return result


def subtract(a: float, b: float) -> float:
    """Subtract b from a"""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b


def divide(a: float, b: float) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def calculate_average(numbers: List[float]) -> float:
    """Calculate average of a list of numbers"""
    if not numbers:
        return 0.0
    
    total = 0
    for num in numbers:
        total = add(total, num)
    
    return divide(total, len(numbers))


def factorial(n: int) -> int:
    """Calculate factorial of n"""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result = multiply(result, i)
    
    return result


class Calculator:
    """A calculator class with memory functionality"""
    
    def __init__(self):
        """Initialize calculator with zero memory"""
        self.memory = 0
        self.history = []
    
    def add_to_memory(self, value: float):
        """Add value to memory"""
        self.memory = add(self.memory, value)
        self._log_operation("add_to_memory", value)
    
    def subtract_from_memory(self, value: float):
        """Subtract value from memory"""
        self.memory = subtract(self.memory, value)
        self._log_operation("subtract_from_memory", value)
    
    def clear_memory(self):
        """Clear memory"""
        self.memory = 0
        self._log_operation("clear_memory", 0)
    
    def get_memory(self) -> float:
        """Get current memory value"""
        return self.memory
    
    def _log_operation(self, operation: str, value: float):
        """Log operation to history"""
        self.history.append({
            'operation': operation,
            'value': value,
            'memory_after': self.memory
        })
    
    def get_history(self) -> List[dict]:
        """Get operation history"""
        return self.history


class ScientificCalculator(Calculator):
    """Extended calculator with scientific functions"""
    
    def power(self, base: float, exponent: float) -> float:
        """Calculate base raised to exponent"""
        result = math.pow(base, exponent)
        self._log_operation("power", result)
        return result
    
    def square_root(self, value: float) -> float:
        """Calculate square root"""
        if value < 0:
            raise ValueError("Cannot calculate square root of negative number")
        
        result = math.sqrt(value)
        self._log_operation("square_root", result)
        return result
    
    def sin(self, angle: float) -> float:
        """Calculate sine of angle in radians"""
        return math.sin(angle)
    
    def cos(self, angle: float) -> float:
        """Calculate cosine of angle in radians"""
        return math.cos(angle)


def main():
    """Main function to demonstrate calculator"""
    print("Calculator Demo")
    
    # Basic operations
    x = 10
    y = 5
    
    sum_result = add(x, y)
    print(f"Sum: {sum_result}")
    
    # Calculate average
    numbers = [1, 2, 3, 4, 5]
    avg = calculate_average(numbers)
    print(f"Average: {avg}")
    
    # Use calculator class
    calc = Calculator()
    calc.add_to_memory(100)
    calc.subtract_from_memory(25)
    print(f"Memory: {calc.get_memory()}")
    
    # Use scientific calculator
    sci_calc = ScientificCalculator()
    result = sci_calc.power(2, 8)
    print(f"2^8 = {result}")
    
    sqrt_result = sci_calc.square_root(16)
    print(f"√16 = {sqrt_result}")


if __name__ == "__main__":
    main()
