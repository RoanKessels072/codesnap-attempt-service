# attempt-service/src/grading.py

import json
import re
import logging
from src.nats_client import NATSClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grading-service")

def extract_test_results(output: str, test_cases_count: int) -> tuple[int, int]:
    """
    Parses the output looking for the RESULTS: X/Y line.
    """
    if not output:
        print("DEBUG: Grading output is empty/None.")
        return 0, test_cases_count
        
    if "RESULTS:" not in output:
        print(f"DEBUG: 'RESULTS:' tag missing. Raw Output from Container:\n{output}")
        return 0, test_cases_count

    try:
        line = next(line for line in output.splitlines() if "RESULTS:" in line)
        passed_str = line.split("RESULTS:")[1].strip()
        passed, total = map(int, passed_str.split("/"))
        return passed, total
    except Exception as e:
        logger.error(f"Error parsing test results: {e}. Output was: {output}")
        return 0, test_cases_count

def calculate_stars(test_pass_rate: float, style_score: float) -> int:
    if test_pass_rate < 1.0:
        return 0
    if style_score >= 8.0:
        return 3
    if style_score >= 6.0:
        return 2
    return 1

async def grade_python_attempt(nats: NATSClient, code: str, function_name: str, test_cases_json) -> dict:
    logger.info(f"Grading Python attempt for function: {function_name}")
    
    if isinstance(test_cases_json, str):
        test_cases = json.loads(test_cases_json)
    else:
        test_cases = test_cases_json
    
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

    print("DEBUG: Sending request to execution.run...")
    try:
        exec_result = await nats.request("execution.run", {
            "language": "python",
            "code": test_code,
            "mode": "run"
        }, timeout=15)

    except Exception as e:
        print(f"DEBUG: NATS Request Failed: {e}")
        return {"stars": 0, "score": 0, "style_score": 0, "feedback": "Execution Service Unavailable", "test_pass_rate": 0}

    if "error" in exec_result and "output" not in exec_result:
        err_msg = exec_result['error']
        if err_msg and isinstance(err_msg, str):
            print(f"DEBUG: Execution Service returned error: {err_msg}")
            return {
                "stars": 0, "score": 0, "style_score": 0, "test_pass_rate": 0,
                "feedback": f"System Error: {err_msg}", "execution_output": err_msg
            }

    lint_result = {}
    try:
        lint_result = await nats.request("execution.run", {
            "language": "python",
            "code": code,
            "mode": "lint"
        }, timeout=10)
    except Exception as e:
        print(f"DEBUG: Linting request failed: {e}")

    output = exec_result.get("output") or ""
    error_output = exec_result.get("error") or ""
    if not isinstance(output, str): output = str(output)
    if not isinstance(error_output, str): error_output = str(error_output)
    
    full_output = output
    if error_output:
        full_output += "\n\n--- ERROR OUTPUT ---\n" + error_output

    print(f"DEBUG: Full Output for Grading:\n{full_output}")

    passed, total = extract_test_results(full_output, len(test_cases))

    lint_output = lint_result.get("output") or ""
    if not isinstance(lint_output, str): lint_output = str(lint_output)

    match = re.search(r"rated at ([\d\.]+)/10", lint_output)
    style_score = float(match.group(1)) if match else 0.0

    test_pass_rate = passed / total if total > 0 else 0.0
    stars = calculate_stars(test_pass_rate, style_score)
    
    score = int(test_pass_rate * 100)

    return {
        "test_pass_rate": test_pass_rate,
        "style_score": style_score,
        "stars": stars,
        "score": score,  # Now included!
        "feedback": lint_output,
        "tests_passed": passed,
        "tests_total": total,
        "execution_output": full_output 
    }

async def grade_javascript_attempt(nats: NATSClient, code: str, function_name: str, test_cases_json) -> dict:
    logger.info(f"Grading JS attempt for function: {function_name}")
    print(f"DEBUG: Starting JS grading for {function_name}")

    if isinstance(test_cases_json, str):
        test_cases = json.loads(test_cases_json)
    else:
        test_cases = test_cases_json    
    
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

    print("DEBUG: Sending JS request to execution.run...")
    try:
        exec_result = await nats.request("execution.run", {
            "language": "javascript",
            "code": test_code,
            "mode": "run"
        }, timeout=15)
    except Exception as e:
        print(f"DEBUG: NATS JS Request Failed: {e}")
        return {"stars": 0, "score": 0, "style_score": 0, "feedback": "Execution Service Unavailable", "test_pass_rate": 0}
    
    if "error" in exec_result and "output" not in exec_result:
        err_msg = exec_result['error']
        if err_msg and isinstance(err_msg, str):
            print(f"DEBUG: Execution Service returned error: {err_msg}")
            return {
                "stars": 0, "score": 0, "style_score": 0, "test_pass_rate": 0,
                "feedback": f"System Error: {err_msg}", "execution_output": err_msg
            }
    
    try:
        lint_result = await nats.request("execution.run", {
            "language": "javascript",
            "code": code,
            "mode": "lint"
        }, timeout=10)
    except Exception as e:
        logger.error(f"NATS linting request failed: {e}")
        lint_result = {}

    output = exec_result.get("output") or ""
    error_output = exec_result.get("error") or ""
    if not isinstance(output, str): output = str(output)
    if not isinstance(error_output, str): error_output = str(error_output)

    full_output = output
    if error_output:
        full_output += "\n--- ERROR ---\n" + error_output
    
    passed, total = extract_test_results(full_output, len(test_cases))

    lint_output = lint_result.get("output") or ""
    if not isinstance(lint_output, str): lint_output = str(lint_output)
    
    style_score = 0.0
    try:
        if lint_output and "problem" not in lint_output.lower():
             style_score = 10.0
        elif lint_output:
             style_score = 5.0
    except Exception:
        style_score = 0.0

    test_pass_rate = passed / total if total > 0 else 0.0
    stars = calculate_stars(test_pass_rate, style_score)
    score = int(test_pass_rate * 100)

    return {
        "test_pass_rate": test_pass_rate,
        "style_score": round(style_score, 2),
        "stars": stars,
        "score": score,
        "feedback": lint_output,
        "tests_passed": passed,
        "tests_total": total,
        "execution_output": full_output
    }

async def grade_submission(nats: NATSClient, code: str, exercise) -> dict:
    language = exercise.language.lower()
    if language == "python":
        return await grade_python_attempt(nats, code, exercise.function_name, exercise.test_cases)
    elif language == "javascript":
        return await grade_javascript_attempt(nats, code, exercise.function_name, exercise.test_cases)
    else:
        logger.error(f"Unsupported language submitted: {language}")
        raise ValueError(f"Unsupported language: {exercise.language}")

async def grade_submission_raw(nats: NATSClient, code: str, language: str, function_name: str, test_cases: list) -> dict:
    lang = language.lower()
    if lang == "python":
        return await grade_python_attempt(nats, code, function_name, test_cases)
    elif lang == "javascript":
        return await grade_javascript_attempt(nats, code, function_name, test_cases)
    else:
        raise ValueError(f"Unsupported language: {language}")