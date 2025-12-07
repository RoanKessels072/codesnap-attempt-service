import json
import re
from src.nats_client import NATSClient


def extract_test_results(output: str, test_cases_count: int) -> tuple[int, int]:
    if not output or "RESULTS:" not in output:
        return 0, test_cases_count
    try:
        line = next(line for line in output.splitlines() if "RESULTS:" in line)
        passed_str = line.split("RESULTS:")[1].strip()
        passed, total = map(int, passed_str.split("/"))
        return passed, total
    except Exception:
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
    if isinstance(test_cases_json, str):
        test_cases = json.loads(test_cases_json)
    else:
        test_cases = test_cases_json
    
    test_code = code + "\n\npassed = 0\ntotal = 0\n\n"
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
        print(f"Test {i+1}: PASSED")
    else:
        print(f"Test {i+1}: FAILED - Expected {{expected}}, got {{result}}")
except Exception as e:
    total += 1
    print(f"Test {i+1}: ERROR - {{str(e)}}")
"""
    test_code += '\nprint(f"RESULTS: {passed}/{total}")\n'

    exec_result = await nats.request("execution.run", {
        "language": "python",
        "code": test_code,
        "mode": "run"
    })
    
    lint_result = await nats.request("execution.run", {
        "language": "python",
        "code": code,
        "mode": "lint"
    })

    output = exec_result.get("output", "")
    passed, total = extract_test_results(output, len(test_cases))

    lint_output = lint_result.get("output", "")
    match = re.search(r"rated at ([\d\.]+)/10", lint_output)
    style_score = float(match.group(1)) if match else 0.0

    test_pass_rate = passed / total if total > 0 else 0.0
    stars = calculate_stars(test_pass_rate, style_score)

    return {
        "test_pass_rate": test_pass_rate,
        "style_score": style_score,
        "stars": stars,
        "feedback": lint_output,
        "tests_passed": passed,
        "tests_total": total
    }

async def grade_javascript_attempt(nats: NATSClient, code: str, function_name: str, test_cases_json) -> dict:
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

    exec_result = await nats.request("execution.run", {
        "language": "javascript",
        "code": test_code,
        "mode": "run"
    })
    
    lint_result = await nats.request("execution.run", {
        "language": "javascript",
        "code": code,
        "mode": "lint"
    })

    output = exec_result.get("output", "")
    passed, total = extract_test_results(output, len(test_cases))

    lint_output = lint_result.get("output", "")
    style_score = 0.0
    
    try:
        json_start = lint_output.find('[')
        if json_start != -1:
            clean_json = lint_output[json_start:]
            reports = json.loads(clean_json)
            messages = reports[0].get("messages", [])
            errors = sum(1 for m in messages if m["severity"] == 2)
            warnings = sum(1 for m in messages if m["severity"] == 1)
            style_score = max(0.0, 10 - errors * 1.5 - warnings * 0.5)
        elif not lint_output.strip():
             style_score = 10.0
    except Exception:
        style_score = 0.0

    test_pass_rate = passed / total if total > 0 else 0.0
    stars = calculate_stars(test_pass_rate, style_score)

    return {
        "test_pass_rate": test_pass_rate,
        "style_score": round(style_score, 2),
        "stars": stars,
        "feedback": lint_output,
        "tests_passed": passed,
        "tests_total": total
    }

async def grade_submission(nats: NATSClient, code: str, exercise) -> dict:
    language = exercise.language.lower()
    if language == "python":
        return await grade_python_attempt(nats, code, exercise.function_name, exercise.test_cases)
    elif language == "javascript":
        return await grade_javascript_attempt(nats, code, exercise.function_name, exercise.test_cases)
    else:
        raise ValueError(f"Unsupported language: {exercise.language}")

async def grade_submission_raw(nats: NATSClient, code: str, language: str, function_name: str, test_cases: list) -> dict:
    lang = language.lower()
    if lang == "python":
        return await grade_python_attempt(nats, code, function_name, test_cases)
    elif lang == "javascript":
        return await grade_javascript_attempt(nats, code, function_name, test_cases)
    else:
        raise ValueError(f"Unsupported language: {language}")