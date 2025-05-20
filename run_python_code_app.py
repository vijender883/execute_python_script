from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import re
import time
import json

app = Flask(__name__)

# Enhanced recorded questions with more metadata
recorded_questions = {
    "twoSum": {
        "main_code": """
if __name__ == "__main__":
    # Test case 1
    arr1 = [0, -1, 2, -3, 1]
    target1 = -2
    print(f"Test case 1: {twoSum(arr1, target1)}")
    
    # Test case 2
    arr2 = [1, 2, 3, 4, 5]
    target2 = 9
    print(f"Test case 2: {twoSum(arr2, target2)}")
    
    # Test case 3
    arr3 = [1, 2, 3, 4, 5]
    target3 = 10
    print(f"Test case 3: {twoSum(arr3, target3)}")
    
    # Test case 4
    arr4 = []
    target4 = 0
    print(f"Test case 4: {twoSum(arr4, target4)}")
""",
        "test_cases": [
            {
                "testCase": 1,
                "description": "Basic test with negative target",
                "input": "arr = [0, -1, 2, -3, 1], target = -2",
                "expectedOutput": "True"
            },
            {
                "testCase": 2,
                "description": "Basic test with positive target",
                "input": "arr = [1, 2, 3, 4, 5], target = 9",
                "expectedOutput": "True"
            },
            {
                "testCase": 3,
                "description": "No sum equals target",
                "input": "arr = [1, 2, 3, 4, 5], target = 10",
                "expectedOutput": "False"
            },
            {
                "testCase": 4,
                "description": "Empty array",
                "input": "arr = [], target = 0",
                "expectedOutput": "False"
            }
        ]
    },
    "longestCommonPrefix": {
        "main_code": """
if __name__ == "__main__":
    # Test case 1
    input1 = ["geeksforgeeks", "geeks", "geek", "geezer"]
    print(f"Test case 1: {longestCommonPrefix(input1)}")
    
    # Test case 2
    input2 = ["apple", "ape", "april"]
    print(f"Test case 2: {longestCommonPrefix(input2)}")
    
    # Test case 3
    input3 = ["dog", "cat", "mouse"]
    print(f"Test case 3: {longestCommonPrefix(input3)}")
    
    # Test case 4
    input4 = ["flower", "flow", "flight"]
    print(f"Test case 4: {longestCommonPrefix(input4)}")
""",
        "test_cases": [
            {
                "testCase": 1,
                "description": "Common prefix 'gee'",
                "input": "strs = [\"geeksforgeeks\", \"geeks\", \"geek\", \"geezer\"]",
                "expectedOutput": "\"gee\""
            },
            {
                "testCase": 2,
                "description": "Common prefix 'ap'",
                "input": "strs = [\"apple\", \"ape\", \"april\"]",
                "expectedOutput": "\"ap\""
            },
            {
                "testCase": 3,
                "description": "No common prefix",
                "input": "strs = [\"dog\", \"cat\", \"mouse\"]",
                "expectedOutput": "\"\""
            },
            {
                "testCase": 4,
                "description": "Common prefix 'fl'",
                "input": "strs = [\"flower\", \"flow\", \"flight\"]",
                "expectedOutput": "\"fl\""
            }
        ]
    }
    # Add more recorded questions as needed
}

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
    
    # Check if function is in recorded questions
    test_code = code
    if function_name in recorded_questions:
        # Add main code and test cases
        test_code += "\n" + recorded_questions[function_name]["main_code"]
    else:
        return jsonify({
            "success": False, 
            "message": f"Function '{function_name}' not found in recorded questions"
        }), 404
    
    # Generate instrumented code to capture execution time and individual results
    instrumented_code = test_code + """
# Add timing and result capturing
import time
import json

def format_result(test_num, output):
    return {
        "testCase": test_num,
        "output": output,
        "executionTime": round(time.time() * 1000) % 100 + 9  # Simulate execution time between 9-109ms
    }

# Run the tests and capture outputs
results = []
lines = globals()["__builtins__"]["print"].__self__._getframe().f_back.f_locals["__name__"]
"""
    
    # Create a temporary file to store the code
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
        temp_filename = temp_file.name
        temp_file.write(test_code.encode('utf-8'))
    
    try:
        # Run the code in a subprocess with timeout
        start_time = time.time()
        result = subprocess.run(
            # for local use './venv/bin/python3'
            ['~/execute_python_script/venv/bin/python3', temp_filename],
            capture_output=True,
            text=True,
            timeout=5  # 5 second timeout to prevent infinite loops
        )
        end_time = time.time()
        
        # Process results
        if result.returncode == 0:
            # Build structured response
            output_lines = result.stdout.strip().split('\n')
            test_cases = recorded_questions[function_name]["test_cases"]
            
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
    app.run(host='0.0.0.0', port=5002, debug=False)