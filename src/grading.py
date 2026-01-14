import json
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grading-service")

def extract_test_results(output: str) -> tuple[int, int, float]:
    """
    Parses the output looking for the RESULTS: X/Y line.
    Returns (passed, total, pass_rate)
    """
    if not output:
        return 0, 0, 0.0
        
    try:
        match = re.search(r"RESULTS:\s*(\d+)/(\d+)", output)
        if match:
            passed = int(match.group(1))
            total = int(match.group(2))
            rate = passed / total if total > 0 else 0.0
            return passed, total, rate
    except Exception:
        pass
        
    return 0, 0, 0.0

def calculate_stars(test_pass_rate: float, style_score: float) -> int:
    if test_pass_rate < 1.0:
        return 0
    if style_score >= 9.0:
        return 3
    if style_score >= 6.0:
        return 2
    return 1

def generate_python_test_code(code: str, function_name: str, test_cases: list) -> str:
    test_code = code + "\n\n# --- TEST HARNESS ---\npassed = 0\ntotal = 0\n\n"
    for i, test in enumerate(test_cases):
        args = ", ".join(repr(a) for a in test["args"])
        expected = repr(test["expected"])
        
        test_code += f"""
try:
    result = {function_name}({args})
    expected = {expected}
    total += 1
    if result == expected:
        passed += 1
        print(f"Test {i+1}: PASSED", flush=True)
    else:
        print(f"Test {i+1}: FAILED - Expected {{expected}}, got {{result}}", flush=True)
except Exception as e:
    total += 1
    print(f"Test {i+1}: ERROR - {{str(e)}}", flush=True)
"""
    test_code += '\nprint(f"RESULTS: {passed}/{total}", flush=True)\n'
    return test_code

def generate_javascript_test_code(code: str, function_name: str, test_cases: list) -> str:
    test_code = code + "\n\nlet passed = 0;\nlet total = 0;\n\n"
    for i, test in enumerate(test_cases):
        args = ", ".join(json.dumps(a) for a in test["args"])
        expected = json.dumps(test["expected"])
        test_code += f"""
try {{
    const result = {function_name}({args});
    const expected = {expected};
    total++;
    if (JSON.stringify(result) === JSON.stringify(expected)) {{
        passed++;
        console.log(`Test {i+1}: PASSED`);
    }} else {{
        console.log(`Test {i+1}: FAILED - Expected ${{expected}}, got ${{result}}`);
    }}
}} catch (e) {{
    total++;
    console.log(`Test {i+1}: ERROR - ${{e.message}}`);
}}
"""
    test_code += '\nconsole.log(`RESULTS: ${passed}/${total}`);\n'
    return test_code

def prepare_grading_job(code: str, language: str, function_name: str, test_cases: list) -> str:
    """
    Generates the code with test harness attached.
    """
    lang = language.lower()
    if lang == "python":
        return generate_python_test_code(code, function_name, test_cases)
    elif lang == "javascript":
        return generate_javascript_test_code(code, function_name, test_cases)
    else:
        raise ValueError(f"Unsupported language: {language}")

def compute_grade_from_results(execution_output: str, lint_output: str) -> dict:
    """
    Pure function to take raw outputs and return the graded result dict.
    """
    if not execution_output: execution_output = ""
    passed, total, pass_rate = extract_test_results(execution_output)
    
    if not lint_output: lint_output = ""
    style_score = 0.0
    
    try:
        match = re.search(r"rated at ([\d\.]+)/10", lint_output)
        if match:
            style_score = float(match.group(1))
        else:
            if lint_output and "problem" not in lint_output.lower():
                 style_score = 10.0
            elif lint_output:
                 style_score = 5.0
    except Exception:
        style_score = 0.0

    stars = calculate_stars(pass_rate, style_score)
    score = int(pass_rate * 100)

    return {
        "stars": stars,
        "score": score,
        "style_score": round(style_score, 2),
        "test_pass_rate": pass_rate,
        "tests_passed": passed,
        "tests_total": total,
        "feedback": lint_output,
        "execution_output": execution_output
    }