from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import re
import time
import json

app = Flask(__name__)

def load_problem_data(function_name):
    """
    Load problem data from a JSON file in the dsa_problems directory.
    The file name should match the function name.
    """
    problem_file_path = os.path.join('dsa_problems', f"{function_name}.json")
    
    # Check if the problem file exists
    if not os.path.exists(problem_file_path):
        return None
    
    # Load and return the problem data
    try:
        with open(problem_file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading problem data: {str(e)}")
        return None

@app.route('/evaluate', methods=['POST'])
def evaluate_code():
    # Get the code directly from the request body as text
    code = request.get_data(as_text=True)
    
    if not code:
        return jsonify({"success": False, "message": "No code provided"}), 400
    
    # Extract function name using regex
    function_match = re.search(r'def\s+([a-zA-Z0-9_]+)\s*\(', code)
    if not function_match:
        return jsonify({"success": False, "message": "Could not identify function name in code"}), 400
    
    function_name = function_match.group(1)
    
    # Load problem data from file
    problem_data = load_problem_data(function_name)
    
    # Check if problem data was found
    if not problem_data:
        return jsonify({
            "success": False, 
            "message": f"Problem data for function '{function_name}' not found"
        }), 404
    
    # Add main code and test cases
    test_code = code + "\n" + problem_data.get("main_code", "")
    
    # Create a temporary file to store the code
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
        temp_filename = temp_file.name
        temp_file.write(test_code.encode('utf-8'))
    
    try:
        # Run the code in a subprocess with timeout
        start_time = time.time()
        result = subprocess.run(
            ['/usr/bin/python3', temp_filename],
            capture_output=True,
            text=True,
            timeout=5  # 5 second timeout to prevent infinite loops
        )
        end_time = time.time()
        
        # Process results
        if result.returncode == 0:
            # Build structured response
            output_lines = result.stdout.strip().split('\n')
            test_cases = problem_data.get("test_cases", [])
            
            results = []
            for i, line in enumerate(output_lines):
                if i < len(test_cases):
                    # Parse the output from the line
                    match = re.search(r'Test case \d+: (.+)', line)
                    actual_output = match.group(1) if match else "Error parsing output"
                    
                    # Create standardized result object
                    test_result = {
                        "testCase": test_cases[i]["testCase"],
                        "description": test_cases[i]["description"],
                        "input": test_cases[i]["input"],
                        "expectedOutput": test_cases[i]["expectedOutput"],
                        "yourOutput": actual_output,
                        "passed": actual_output.strip() == test_cases[i]["expectedOutput"].strip(),
                        "executionTime": round((end_time - start_time) * 1000 / len(output_lines), 2)  # Approximate execution time per test
                    }
                    results.append(test_result)
            
            return jsonify({
                "success": True,
                "results": results
            })
        else:
            return jsonify({
                "success": False,
                "message": "Code execution failed",
                "error": result.stderr
            })
    
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "message": "Code execution timed out (limit: 5 seconds)"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error executing code: {str(e)}"
        })
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    # Create the dsa_problems directory if it doesn't exist
    os.makedirs('dsa_problems', exist_ok=True)
    app.run(host='0.0.0.0', port=5002, debug=False)