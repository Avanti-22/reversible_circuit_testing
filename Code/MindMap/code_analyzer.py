#!/usr/bin/env python3
"""
Python Code Analyzer
Generates flowcharts, pseudocode, and algorithms with detailed call hierarchy
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict


class CodeAnalyzer:
    """Analyzes Python code to extract structure and generate documentation"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.tree = None
        self.functions = {}
        self.classes = {}
        self.call_graph = defaultdict(list)
        self.imports = []
        self.global_vars = []
        
    def parse_file(self):
        """Parse the Python file into an AST"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        self.tree = ast.parse(code, filename=self.filepath)
        
    def analyze(self):
        """Perform complete analysis of the code"""
        self.parse_file()
        self._extract_imports()
        self._extract_global_variables()
        self._extract_functions()
        self._extract_classes()
        self._build_call_graph()
        
    def _extract_imports(self):
        """Extract all import statements"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    self.imports.append({
                        'type': 'from',
                        'module': node.module,
                        'name': alias.name,
                        'alias': alias.asname
                    })
    
    def _extract_global_variables(self):
        """Extract global variable assignments"""
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.global_vars.append({
                            'name': target.id,
                            'lineno': node.lineno
                        })
    
    def _extract_functions(self):
        """Extract all function definitions"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                # Skip methods (will be handled with classes)
                if not self._is_method(node):
                    self.functions[node.name] = self._analyze_function(node)
    
    def _extract_classes(self):
        """Extract all class definitions"""
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                methods = {}
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods[item.name] = self._analyze_function(item, is_method=True)
                
                self.classes[node.name] = {
                    'name': node.name,
                    'lineno': node.lineno,
                    'bases': [self._get_name(base) for base in node.bases],
                    'methods': methods,
                    'docstring': ast.get_docstring(node)
                }
    
    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function is a method of a class"""
        for class_node in ast.walk(self.tree):
            if isinstance(class_node, ast.ClassDef):
                if node in class_node.body:
                    return True
        return False
    
    def _analyze_function(self, node: ast.FunctionDef, is_method: bool = False) -> Dict:
        """Analyze a function and extract its structure"""
        params = []
        for arg in node.args.args:
            params.append(arg.arg)
        
        # Extract control flow
        control_flow = self._extract_control_flow(node)
        
        # Extract function calls
        calls = self._extract_calls(node)
        
        return {
            'name': node.name,
            'lineno': node.lineno,
            'params': params,
            'returns': self._has_return(node),
            'docstring': ast.get_docstring(node),
            'control_flow': control_flow,
            'calls': calls,
            'is_method': is_method
        }
    
    def _extract_control_flow(self, node: ast.AST) -> List[Dict]:
        """Extract control flow structures (if, for, while, try, etc.)"""
        flow = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                flow.append({
                    'type': 'if',
                    'lineno': child.lineno,
                    'test': ast.unparse(child.test) if hasattr(ast, 'unparse') else 'condition'
                })
            elif isinstance(child, ast.For):
                flow.append({
                    'type': 'for',
                    'lineno': child.lineno,
                    'target': ast.unparse(child.target) if hasattr(ast, 'unparse') else 'variable',
                    'iter': ast.unparse(child.iter) if hasattr(ast, 'unparse') else 'iterable'
                })
            elif isinstance(child, ast.While):
                flow.append({
                    'type': 'while',
                    'lineno': child.lineno,
                    'test': ast.unparse(child.test) if hasattr(ast, 'unparse') else 'condition'
                })
            elif isinstance(child, ast.Try):
                flow.append({
                    'type': 'try',
                    'lineno': child.lineno,
                    'handlers': len(child.handlers)
                })
            elif isinstance(child, ast.With):
                flow.append({
                    'type': 'with',
                    'lineno': child.lineno
                })
        
        return flow
    
    def _extract_calls(self, node: ast.AST) -> List[str]:
        """Extract all function calls within a node"""
        calls = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child.func)
                if call_name:
                    calls.append(call_name)
        
        return calls
    
    def _get_call_name(self, node: ast.AST) -> str:
        """Get the name of a function call"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""
    
    def _get_name(self, node: ast.AST) -> str:
        """Get the name from an AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ""
    
    def _has_return(self, node: ast.FunctionDef) -> bool:
        """Check if a function has a return statement"""
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                return True
        return False
    
    def _build_call_graph(self):
        """Build a call graph showing which functions call which"""
        # For standalone functions
        for func_name, func_info in self.functions.items():
            for call in func_info['calls']:
                self.call_graph[func_name].append(call)
        
        # For class methods
        for class_name, class_info in self.classes.items():
            for method_name, method_info in class_info['methods'].items():
                full_name = f"{class_name}.{method_name}"
                for call in method_info['calls']:
                    self.call_graph[full_name].append(call)


class FlowchartGenerator:
    """Generates Mermaid flowchart syntax from analyzed code"""
    
    def __init__(self, analyzer: CodeAnalyzer):
        self.analyzer = analyzer
        self.node_counter = 0
        
    def _get_node_id(self):
        """Generate unique node ID"""
        self.node_counter += 1
        return f"N{self.node_counter}"
    
    def _sanitize_text(self, text: str, max_length: int = 50) -> str:
        """Sanitize text for Mermaid"""
        # Remove problematic characters and limit length
        text = text.replace('"', "'").replace('[', '(').replace(']', ')')
        text = text.replace('{', '(').replace('}', ')')
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        return text
        
    def generate(self) -> str:
        """Generate complete flowchart - simplified overview"""
        lines = ["flowchart TD"]
        lines.append("    Start([Start Program])")
        
        prev = "Start"
        
        # Add imports
        if self.analyzer.imports:
            lines.append("    Start --> Imports[Import Modules]")
            prev = "Imports"
        
        # Add global variables
        if self.analyzer.global_vars:
            lines.append(f"    {prev} --> Globals[Initialize Global Variables]")
            prev = "Globals"
        
        # Track last node for final connection
        last_node = prev
        
        # Add functions
        func_count = 0
        for func_name, func_info in self.analyzer.functions.items():
            func_node = f"Func{func_count}"
            safe_func_name = self._sanitize_text(func_name, 30)
            lines.append(f"    {last_node} --> {func_node}[\"Function: {safe_func_name}\"]")
            
            # Add function details as connected nodes
            if func_info['params']:
                param_node = f"Func{func_count}P"
                params_str = self._sanitize_text(", ".join(func_info['params'][:3]))
                if len(func_info['params']) > 3:
                    params_str += "..."
                lines.append(f"    {func_node} -.-> {param_node}[\"Params: {params_str}\"]")
            
            # Add control flow summary
            if func_info['control_flow']:
                flow_node = f"Func{func_count}F"
                flow_types = [f['type'] for f in func_info['control_flow']]
                flow_summary = self._sanitize_text(", ".join(set(flow_types)), 30)
                lines.append(f"    {func_node} -.-> {flow_node}{{\"Contains: {flow_summary}\"}}")
            
            last_node = func_node
            func_count += 1
        
        # Add classes
        class_count = 0
        for class_name, class_info in self.analyzer.classes.items():
            class_node = f"Class{class_count}"
            safe_class_name = self._sanitize_text(class_name, 30)
            lines.append(f"    {last_node} --> {class_node}[\"Class: {safe_class_name}\"]")
            
            # Add inheritance info
            if class_info['bases']:
                inherit_node = f"Class{class_count}I"
                bases_str = self._sanitize_text(", ".join(class_info['bases']), 30)
                lines.append(f"    {class_node} -.-> {inherit_node}[\"Inherits: {bases_str}\"]")
            
            # Add methods count
            method_count = len(class_info['methods'])
            method_info_node = f"Class{class_count}M"
            lines.append(f"    {class_node} -.-> {method_info_node}[\"Methods: {method_count}\"]")
            
            last_node = class_node
            class_count += 1
        
        lines.append(f"    {last_node} --> End([End Program])")
        
        # Add styling
        lines.append("")
        lines.append("    style Start fill:#90EE90")
        lines.append("    style End fill:#FFB6C1")
        
        return "\n".join(lines)
    
    def generate_detailed_function_flowchart(self, func_name: str) -> str:
        """Generate detailed flowchart for a specific function"""
        func_info = None
        
        # Find the function
        if func_name in self.analyzer.functions:
            func_info = self.analyzer.functions[func_name]
        else:
            # Check in class methods
            for class_name, class_info in self.analyzer.classes.items():
                if func_name in class_info['methods']:
                    func_info = class_info['methods'][func_name]
                    break
        
        if not func_info:
            return f"Function '{func_name}' not found"
        
        lines = [f"flowchart TD"]
        lines.append(f"    Start([\"Start: {func_name}\"])")
        
        prev_node = "Start"
        node_count = 0
        
        # Parameters
        if func_info['params']:
            param_node = f"P{node_count}"
            params_str = self._sanitize_text(", ".join(func_info['params']))
            lines.append(f"    {prev_node} --> {param_node}[\"Input: {params_str}\"]")
            prev_node = param_node
            node_count += 1
        
        # Control flow and logic
        for i, flow in enumerate(func_info['control_flow']):
            flow_node = f"F{node_count}"
            
            if flow['type'] == 'if':
                condition = self._sanitize_text(flow.get('test', 'condition'))
                lines.append(f"    {prev_node} --> {flow_node}{{\"{condition}?\"}}")
                
                # Add branches
                true_node = f"F{node_count}T"
                false_node = f"F{node_count}F"
                lines.append(f"    {flow_node} -->|Yes| {true_node}[\"True branch\"]")
                lines.append(f"    {flow_node} -->|No| {false_node}[\"False branch\"]")
                
                # Merge point
                merge_node = f"F{node_count}M"
                lines.append(f"    {true_node} --> {merge_node}[ ]")
                lines.append(f"    {false_node} --> {merge_node}")
                prev_node = merge_node
                
            elif flow['type'] == 'for':
                target = self._sanitize_text(flow.get('target', 'item'))
                iter_val = self._sanitize_text(flow.get('iter', 'collection'))
                lines.append(f"    {prev_node} --> {flow_node}[\"For {target} in {iter_val}\"]")
                
                # Loop body
                body_node = f"F{node_count}B"
                lines.append(f"    {flow_node} --> {body_node}[\"Loop body\"]")
                lines.append(f"    {body_node} --> {flow_node}")
                
                # Exit
                exit_node = f"F{node_count}E"
                lines.append(f"    {flow_node} --> {exit_node}[\"Continue\"]")
                prev_node = exit_node
                
            elif flow['type'] == 'while':
                condition = self._sanitize_text(flow.get('test', 'condition'))
                lines.append(f"    {prev_node} --> {flow_node}{{\"{condition}?\"}}")
                
                # Loop body
                body_node = f"F{node_count}B"
                exit_node = f"F{node_count}E"
                lines.append(f"    {flow_node} -->|Yes| {body_node}[\"Loop body\"]")
                lines.append(f"    {body_node} --> {flow_node}")
                lines.append(f"    {flow_node} -->|No| {exit_node}[\"Continue\"]")
                prev_node = exit_node
                
            elif flow['type'] == 'try':
                lines.append(f"    {prev_node} --> {flow_node}[\"Try block\"]")
                
                # Success and error paths
                success_node = f"F{node_count}S"
                error_node = f"F{node_count}E"
                merge_node = f"F{node_count}M"
                
                lines.append(f"    {flow_node} --> {success_node}[\"Success\"]")
                lines.append(f"    {flow_node} -.-> {error_node}[\"Exception handler\"]")
                lines.append(f"    {success_node} --> {merge_node}[ ]")
                lines.append(f"    {error_node} --> {merge_node}")
                prev_node = merge_node
            
            node_count += 1
        
        # Function calls
        if func_info['calls']:
            call_node = f"C{node_count}"
            calls_str = self._sanitize_text(", ".join(list(set(func_info['calls']))[:3]))
            if len(set(func_info['calls'])) > 3:
                calls_str += "..."
            lines.append(f"    {prev_node} --> {call_node}[\"Calls: {calls_str}\"]")
            prev_node = call_node
            node_count += 1
        
        # Return
        if func_info['returns']:
            lines.append(f"    {prev_node} --> End([\"Return result\"])")
        else:
            lines.append(f"    {prev_node} --> End([\"End\"])")
        
        return "\n".join(lines)


class PseudocodeGenerator:
    """Generates pseudocode from analyzed code"""
    
    def __init__(self, analyzer: CodeAnalyzer):
        self.analyzer = analyzer
    
    def generate(self) -> str:
        """Generate complete pseudocode"""
        lines = ["PROGRAM " + Path(self.analyzer.filepath).stem]
        lines.append("")
        
        # Imports
        if self.analyzer.imports:
            lines.append("// Import required modules")
            for imp in self.analyzer.imports:
                if imp['type'] == 'import':
                    lines.append(f"IMPORT {imp['module']}")
                else:
                    lines.append(f"IMPORT {imp['name']} FROM {imp['module']}")
            lines.append("")
        
        # Global variables
        if self.analyzer.global_vars:
            lines.append("// Global variables")
            for var in self.analyzer.global_vars:
                lines.append(f"DECLARE {var['name']}")
            lines.append("")
        
        # Functions
        for func_name, func_info in self.analyzer.functions.items():
            lines.extend(self._generate_function_pseudocode(func_name, func_info))
            lines.append("")
        
        # Classes
        for class_name, class_info in self.analyzer.classes.items():
            lines.append(f"CLASS {class_name}")
            if class_info['bases']:
                lines.append(f"    INHERITS FROM {', '.join(class_info['bases'])}")
            lines.append("")
            
            for method_name, method_info in class_info['methods'].items():
                lines.extend(self._generate_function_pseudocode(
                    method_name, method_info, indent=1, is_method=True
                ))
                lines.append("")
            
            lines.append("END CLASS")
            lines.append("")
        
        lines.append("END PROGRAM")
        
        return "\n".join(lines)
    
    def _generate_function_pseudocode(self, func_name: str, func_info: Dict, 
                                     indent: int = 0, is_method: bool = False) -> List[str]:
        """Generate pseudocode for a single function"""
        lines = []
        prefix = "    " * indent
        
        # Function signature
        params = ", ".join(func_info['params'])
        func_type = "METHOD" if is_method else "FUNCTION"
        lines.append(f"{prefix}{func_type} {func_name}({params})")
        
        if func_info['docstring']:
            lines.append(f"{prefix}    // {func_info['docstring'].split(chr(10))[0]}")
        
        # Control flow
        for flow in func_info['control_flow']:
            if flow['type'] == 'if':
                lines.append(f"{prefix}    IF {flow['test']} THEN")
                lines.append(f"{prefix}        // conditional logic")
                lines.append(f"{prefix}    END IF")
            elif flow['type'] == 'for':
                lines.append(f"{prefix}    FOR {flow['target']} IN {flow['iter']} DO")
                lines.append(f"{prefix}        // loop body")
                lines.append(f"{prefix}    END FOR")
            elif flow['type'] == 'while':
                lines.append(f"{prefix}    WHILE {flow['test']} DO")
                lines.append(f"{prefix}        // loop body")
                lines.append(f"{prefix}    END WHILE")
            elif flow['type'] == 'try':
                lines.append(f"{prefix}    TRY")
                lines.append(f"{prefix}        // protected code")
                lines.append(f"{prefix}    CATCH exception")
                lines.append(f"{prefix}        // error handling")
                lines.append(f"{prefix}    END TRY")
        
        # Function calls
        if func_info['calls']:
            lines.append(f"{prefix}    // Calls: {', '.join(set(func_info['calls']))}")
        
        if func_info['returns']:
            lines.append(f"{prefix}    RETURN result")
        
        lines.append(f"{prefix}END {func_type}")
        
        return lines


class AlgorithmGenerator:
    """Generates step-by-step algorithm description"""
    
    def __init__(self, analyzer: CodeAnalyzer):
        self.analyzer = analyzer
    
    def generate(self) -> str:
        """Generate complete algorithm description"""
        lines = [f"ALGORITHM: {Path(self.analyzer.filepath).stem}"]
        lines.append("=" * 60)
        lines.append("")
        
        # Overview
        lines.append("OVERVIEW:")
        lines.append(f"  - Total Functions: {len(self.analyzer.functions)}")
        lines.append(f"  - Total Classes: {len(self.analyzer.classes)}")
        lines.append(f"  - Total Imports: {len(self.analyzer.imports)}")
        lines.append("")
        
        # Step-by-step algorithm
        step = 1
        
        lines.append("ALGORITHM STEPS:")
        lines.append("")
        
        # Imports
        if self.analyzer.imports:
            lines.append(f"Step {step}: Import Dependencies")
            step += 1
            for imp in self.analyzer.imports:
                if imp['type'] == 'import':
                    lines.append(f"  - Import module: {imp['module']}")
                else:
                    lines.append(f"  - Import {imp['name']} from {imp['module']}")
            lines.append("")
        
        # Global initialization
        if self.analyzer.global_vars:
            lines.append(f"Step {step}: Initialize Global Variables")
            step += 1
            for var in self.analyzer.global_vars:
                lines.append(f"  - Declare and initialize: {var['name']}")
            lines.append("")
        
        # Functions
        for func_name, func_info in self.analyzer.functions.items():
            lines.append(f"Step {step}: Define Function '{func_name}'")
            step += 1
            lines.extend(self._generate_function_algorithm(func_info, indent=1))
            lines.append("")
        
        # Classes
        for class_name, class_info in self.analyzer.classes.items():
            lines.append(f"Step {step}: Define Class '{class_name}'")
            step += 1
            
            if class_info['bases']:
                lines.append(f"  - Inherits from: {', '.join(class_info['bases'])}")
            
            for method_name, method_info in class_info['methods'].items():
                lines.append(f"  - Method: {method_name}")
                lines.extend(self._generate_function_algorithm(method_info, indent=2))
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_function_algorithm(self, func_info: Dict, indent: int = 0) -> List[str]:
        """Generate algorithm steps for a function"""
        lines = []
        prefix = "  " * indent
        
        if func_info['params']:
            lines.append(f"{prefix}- Parameters: {', '.join(func_info['params'])}")
        
        if func_info['docstring']:
            lines.append(f"{prefix}- Purpose: {func_info['docstring'].split(chr(10))[0]}")
        
        if func_info['control_flow']:
            lines.append(f"{prefix}- Control Flow:")
            for flow in func_info['control_flow']:
                lines.append(f"{prefix}  * {flow['type'].upper()} statement at line {flow['lineno']}")
        
        if func_info['calls']:
            lines.append(f"{prefix}- Function Calls: {', '.join(set(func_info['calls']))}")
        
        if func_info['returns']:
            lines.append(f"{prefix}- Returns: value")
        
        return lines


class CallHierarchyGenerator:
    """Generates detailed call hierarchy visualization"""
    
    def __init__(self, analyzer: CodeAnalyzer):
        self.analyzer = analyzer
    
    def generate(self) -> str:
        """Generate call hierarchy"""
        lines = ["CALL HIERARCHY"]
        lines.append("=" * 60)
        lines.append("")
        
        # Build reverse call graph (who calls whom)
        called_by = defaultdict(list)
        for caller, callees in self.analyzer.call_graph.items():
            for callee in callees:
                called_by[callee].append(caller)
        
        # Display hierarchy
        lines.append("Function Call Graph:")
        lines.append("")
        
        for func_name in sorted(self.analyzer.call_graph.keys()):
            calls = self.analyzer.call_graph[func_name]
            lines.append(f"{func_name}()")
            
            if calls:
                lines.append("  ├─ Calls:")
                for call in sorted(set(calls)):
                    lines.append(f"  │  └─ {call}()")
            
            if func_name in called_by:
                lines.append("  └─ Called by:")
                for caller in sorted(set(called_by[func_name])):
                    lines.append(f"     └─ {caller}()")
            
            lines.append("")
        
        # Execution flow analysis
        lines.append("=" * 60)
        lines.append("EXECUTION FLOW ANALYSIS:")
        lines.append("")
        
        # Find entry points (functions not called by others)
        all_funcs = set(self.analyzer.call_graph.keys())
        all_called = set()
        for calls in self.analyzer.call_graph.values():
            all_called.update(calls)
        
        entry_points = all_funcs - all_called
        
        if entry_points:
            lines.append("Entry Points (not called by other functions):")
            for entry in sorted(entry_points):
                lines.append(f"  - {entry}()")
                self._trace_calls(entry, lines, visited=set(), depth=1)
            lines.append("")
        
        return "\n".join(lines)
    
    def _trace_calls(self, func_name: str, lines: List[str], visited: Set[str], depth: int, max_depth: int = 5):
        """Recursively trace function calls"""
        if depth > max_depth or func_name in visited:
            return
        
        visited.add(func_name)
        calls = self.analyzer.call_graph.get(func_name, [])
        
        for call in sorted(set(calls)):
            prefix = "    " * depth
            lines.append(f"{prefix}└─> {call}()")
            
            if call in self.analyzer.call_graph:
                self._trace_calls(call, lines, visited, depth + 1, max_depth)


def generate_all_documentation(filepath: str, output_dir: str = None):
    """Generate all documentation for a Python file"""
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Set output directory
    if output_dir is None:
        output_dir = os.path.dirname(filepath) or "."
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze code
    print(f"Analyzing {filepath}...")
    analyzer = CodeAnalyzer(filepath)
    analyzer.analyze()
    
    base_name = Path(filepath).stem
    
    # Generate flowchart (overview)
    print("Generating overview flowchart...")
    flowchart_gen = FlowchartGenerator(analyzer)
    flowchart = flowchart_gen.generate()
    
    flowchart_file = os.path.join(output_dir, f"{base_name}_flowchart.mermaid")
    with open(flowchart_file, 'w', encoding='utf-8') as f:
        f.write(flowchart)
    print(f"  ✓ Overview flowchart saved to: {flowchart_file}")
    
    # Generate detailed flowcharts for each function
    print("Generating detailed function flowcharts...")
    detailed_flowcharts = []
    
    for func_name in analyzer.functions.keys():
        detailed_flow = flowchart_gen.generate_detailed_function_flowchart(func_name)
        detailed_file = os.path.join(output_dir, f"{base_name}_flowchart_{func_name}.mermaid")
        with open(detailed_file, 'w', encoding='utf-8') as f:
            f.write(detailed_flow)
        detailed_flowcharts.append(detailed_file)
        print(f"  ✓ Detailed flowchart for '{func_name}' saved")
    
    # Generate pseudocode
    print("Generating pseudocode...")
    pseudocode_gen = PseudocodeGenerator(analyzer)
    pseudocode = pseudocode_gen.generate()
    
    pseudocode_file = os.path.join(output_dir, f"{base_name}_pseudocode.txt")
    with open(pseudocode_file, 'w', encoding='utf-8') as f:
        f.write(pseudocode)
    print(f"  ✓ Pseudocode saved to: {pseudocode_file}")
    
    # Generate algorithm
    print("Generating algorithm...")
    algorithm_gen = AlgorithmGenerator(analyzer)
    algorithm = algorithm_gen.generate()
    
    algorithm_file = os.path.join(output_dir, f"{base_name}_algorithm.txt")
    with open(algorithm_file, 'w', encoding='utf-8') as f:
        f.write(algorithm)
    print(f"  ✓ Algorithm saved to: {algorithm_file}")
    
    # Generate call hierarchy
    print("Generating call hierarchy...")
    hierarchy_gen = CallHierarchyGenerator(analyzer)
    hierarchy = hierarchy_gen.generate()
    
    hierarchy_file = os.path.join(output_dir, f"{base_name}_call_hierarchy.txt")
    with open(hierarchy_file, 'w', encoding='utf-8') as f:
        f.write(hierarchy)
    print(f"  ✓ Call hierarchy saved to: {hierarchy_file}")
    
    # Generate comprehensive report
    print("Generating comprehensive report...")
    report = []
    report.append("=" * 80)
    report.append(f"CODE ANALYSIS REPORT: {Path(filepath).name}")
    report.append("=" * 80)
    report.append("")
    report.append(algorithm)
    report.append("\n" + "=" * 80 + "\n")
    report.append(hierarchy)
    report.append("\n" + "=" * 80 + "\n")
    report.append("PSEUDOCODE:")
    report.append("=" * 80)
    report.append(pseudocode)
    
    report_file = os.path.join(output_dir, f"{base_name}_complete_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    print(f"  ✓ Complete report saved to: {report_file}")
    
    print("\n✅ Analysis complete!")
    print(f"\nGenerated files:")
    print(f"  1. {flowchart_file} (overview)")
    if detailed_flowcharts:
        print(f"  2. {len(detailed_flowcharts)} detailed function flowcharts")
        print(f"  3. {pseudocode_file}")
        print(f"  4. {algorithm_file}")
        print(f"  5. {hierarchy_file}")
        print(f"  6. {report_file}")
    else:
        print(f"  2. {pseudocode_file}")
        print(f"  3. {algorithm_file}")
        print(f"  4. {hierarchy_file}")
        print(f"  5. {report_file}")
    
    return {
        'flowchart': flowchart_file,
        'detailed_flowcharts': detailed_flowcharts,
        'pseudocode': pseudocode_file,
        'algorithm': algorithm_file,
        'hierarchy': hierarchy_file,
        'report': report_file
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python code_analyzer.py <python_file> [output_directory]")
        print("\nExample:")
        print("  python code_analyzer.py my_script.py")
        print("  python code_analyzer.py my_script.py ./output")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        generate_all_documentation(input_file, output_dir)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)