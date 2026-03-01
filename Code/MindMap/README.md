# Python Code Analyzer

A comprehensive tool that analyzes Python code files and automatically generates:
- **Flowcharts** (in Mermaid format)
- **Pseudocode**
- **Algorithm descriptions**
- **Detailed call hierarchy**

## Features

✨ **Comprehensive Analysis**
- Extracts all functions, classes, and methods
- Identifies control flow structures (if, for, while, try-except)
- Builds complete call graphs
- Tracks imports and global variables
- Analyzes class inheritance

📊 **Multiple Output Formats**
- **Flowchart**: Visual representation in Mermaid syntax
- **Pseudocode**: Language-agnostic pseudocode
- **Algorithm**: Step-by-step algorithm description
- **Call Hierarchy**: Detailed function call tree with execution flow
- **Complete Report**: Combined comprehensive report

## Installation

No additional dependencies required! Uses only Python standard library.

```bash
# Make the script executable (optional)
chmod +x code_analyzer.py
```

## Usage

### Basic Usage

```bash
python code_analyzer.py <input_file.py> [output_directory]
```

### Examples

```bash
# Analyze a Python file (outputs to current directory)
python code_analyzer.py my_script.py

# Analyze and save to specific directory
python code_analyzer.py my_script.py ./analysis_output

# Analyze the example calculator
python code_analyzer.py example_calculator.py
```

## Output Files

The tool generates 5 files:

1. **`<filename>_flowchart.mermaid`**
   - Mermaid flowchart diagram
   - Can be visualized using Mermaid Live Editor or GitHub

2. **`<filename>_pseudocode.txt`**
   - Language-agnostic pseudocode
   - Shows program structure and logic flow

3. **`<filename>_algorithm.txt`**
   - Step-by-step algorithm description
   - Includes overview and detailed steps

4. **`<filename>_call_hierarchy.txt`**
   - Function call graph
   - Shows which functions call which
   - Execution flow analysis with entry points

5. **`<filename>_complete_report.txt`**
   - Comprehensive report combining all analyses
   - Perfect for documentation

## Visualizing Flowcharts

The generated `.mermaid` files can be visualized using:

1. **Mermaid Live Editor**: https://mermaid.live/
   - Copy and paste the content

2. **VS Code Extension**: 
   - Install "Markdown Preview Mermaid Support"
   - Create a markdown file with:
   ```markdown
   ```mermaid
   [paste flowchart content here]
   ```
   ```

3. **GitHub/GitLab**:
   - Mermaid diagrams render automatically in markdown files

## Example Output

### Pseudocode Example
```
PROGRAM example_calculator

// Import required modules
IMPORT math
IMPORT List FROM typing

FUNCTION add(a, b)
    // Add two numbers
    IF DEBUG_MODE THEN
        // conditional logic
    END IF
    RETURN result
END FUNCTION

CLASS Calculator
    METHOD __init__(self)
        // Initialize calculator with zero memory
    END METHOD
    
    METHOD add_to_memory(self, value)
        // Add value to memory
        // Calls: add, self._log_operation
    END METHOD
END CLASS
```

### Call Hierarchy Example
```
CALL HIERARCHY
============================================================

Function Call Graph:

add()
  ├─ Calls:
  │  └─ print()
  └─ Called by:
     └─ Calculator.add_to_memory()
     └─ calculate_average()
     └─ main()

calculate_average()
  ├─ Calls:
  │  └─ add()
  │  └─ divide()
  │  └─ len()
  └─ Called by:
     └─ main()
```

## Use Cases

### 1. Documentation Generation
Automatically generate documentation for your codebase:
```bash
python code_analyzer.py src/main.py docs/
```

### 2. Code Review
Understand code structure before reviewing:
```bash
python code_analyzer.py feature_branch.py review/
```

### 3. Learning & Education
Students can visualize how their code flows:
```bash
python code_analyzer.py homework.py
```

### 4. Legacy Code Analysis
Understand unfamiliar or legacy code:
```bash
python code_analyzer.py legacy_system.py analysis/
```

### 5. Refactoring Planning
Identify dependencies before refactoring:
```bash
python code_analyzer.py old_module.py refactor_plan/
```

## What Gets Analyzed

### Code Elements
- ✅ Function definitions
- ✅ Class definitions
- ✅ Methods (including inheritance)
- ✅ Import statements
- ✅ Global variables
- ✅ Function parameters and return values
- ✅ Docstrings

### Control Flow
- ✅ If statements
- ✅ For loops
- ✅ While loops
- ✅ Try-except blocks
- ✅ With statements

### Relationships
- ✅ Function calls
- ✅ Method calls
- ✅ Class inheritance
- ✅ Call hierarchy
- ✅ Execution flow

## Programmatic Usage

You can also use the analyzer in your own Python scripts:

```python
from code_analyzer import generate_all_documentation

# Generate all documentation
files = generate_all_documentation('my_script.py', 'output/')

print(f"Flowchart: {files['flowchart']}")
print(f"Pseudocode: {files['pseudocode']}")
print(f"Algorithm: {files['algorithm']}")
print(f"Call Hierarchy: {files['hierarchy']}")
print(f"Complete Report: {files['report']}")
```

### Advanced Usage

```python
from code_analyzer import CodeAnalyzer, FlowchartGenerator, PseudocodeGenerator

# Analyze code
analyzer = CodeAnalyzer('script.py')
analyzer.analyze()

# Access analysis results
print(f"Functions: {list(analyzer.functions.keys())}")
print(f"Classes: {list(analyzer.classes.keys())}")
print(f"Call graph: {dict(analyzer.call_graph)}")

# Generate specific outputs
flowchart_gen = FlowchartGenerator(analyzer)
flowchart = flowchart_gen.generate()

pseudocode_gen = PseudocodeGenerator(analyzer)
pseudocode = pseudocode_gen.generate()
```

## Limitations

- Only analyzes Python 3 code
- Dynamic code execution is not analyzed
- External module dependencies are noted but not deeply analyzed
- Complex lambda functions may be simplified in output
- Decorators are not explicitly shown in flowcharts

## Tips for Best Results

1. **Add docstrings** to your functions and classes - they'll appear in the output
2. **Use descriptive names** - they make the generated documentation clearer
3. **Keep functions focused** - easier to understand in flowcharts
4. **Comment your code** - context helps in analysis

## Troubleshooting

### Syntax Errors
```
Error: invalid syntax
```
**Solution**: Ensure your Python file has valid syntax. Run `python -m py_compile your_file.py` first.

### Import Errors
The analyzer itself shouldn't raise import errors, but if analyzing code with missing dependencies, it will note the imports but continue analysis.

### Large Files
For very large files (1000+ lines), the flowchart may become complex. Consider analyzing modules separately.

## Contributing

Feel free to extend the analyzer! Key areas for enhancement:
- Add more control flow structures
- Improve flowchart layout
- Add support for type hints analysis
- Generate UML diagrams
- Add complexity metrics

## License

Free to use and modify for any purpose.

## Example Files Included

- `code_analyzer.py` - The main analyzer tool
- `example_calculator.py` - Sample Python file for testing

Try it out:
```bash
python code_analyzer.py example_calculator.py
```

## Output Example Structure

```
your_script.py
├── your_script_flowchart.mermaid      # Flowchart visualization
├── your_script_pseudocode.txt         # Pseudocode representation
├── your_script_algorithm.txt          # Algorithm steps
├── your_script_call_hierarchy.txt     # Call graph & execution flow
└── your_script_complete_report.txt    # Combined comprehensive report
```

---

**Happy Code Analysis!** 🚀
