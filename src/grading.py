import subprocess
import tempfile
import os
import json
import sys

def grade_python_attempt(code: str, function_name: str, test_cases: list) -> dict:
    """Grade a Python code submission"""
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
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w')
    tmp_name = tmp.name
    try:
        tmp.write(test_code)
        tmp.flush()
        tmp.close()
        
        result = subprocess.run(
            [sys.executable, tmp_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            text=True
        )
        
        output = result.stdout
        if "RESULTS:" in output:
            line = next(line for line in output.splitlines() if "RESULTS:" in line)
            passed_str = line.split("RESULTS:")[1].strip()
            passed, total = map(int, passed_str.split("/"))
        else:
            passed, total = 0, len(test_cases)
            
        test_pass_rate = passed / total if total > 0 else 0.0
        
        score = int((passed / total) * 100) if total > 0 else 0
        
        if test_pass_rate >= 1.0:
            stars = 3
        elif test_pass_rate >= 0.7:
            stars = 2
        elif test_pass_rate >= 0.4:
            stars = 1
        else:
            stars = 0
            
        return {
            "score": score,
            "stars": stars,
            "tests_passed": passed,
            "tests_total": total,
            "test_pass_rate": test_pass_rate
        }
    except subprocess.TimeoutExpired:
        return {"score": 0, "stars": 0, "tests_passed": 0, "tests_total": len(test_cases), "test_pass_rate": 0.0}
    except Exception as e:
        print(f"Error grading: {e}")
        return {"score": 0, "stars": 0, "tests_passed": 0, "tests_total": len(test_cases), "test_pass_rate": 0.0}
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except:
            pass