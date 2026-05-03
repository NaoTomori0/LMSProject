"""Пример кода для проверки заданий"""

import sys, json, subprocess, tempfile, os, shutil

"""ТЕСТЫ С БАЛЛАМИ
Поле "score" – сколько баллов даётся за прохождение теста.
Если не указано, баллы распределятся поровну (общий максимум = 100)."""
test_cases = [
    {"input": "4\n", "expected": "Even", "score": 30},
    {"input": "7\n", "expected": "Odd", "score": 40},
    {"input": "0\n", "expected": "Even", "score": 30},
]


"""ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ"""


def _to_extension(src_path, extension):
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    fd, tmp_path = tempfile.mkstemp(suffix="." + extension)
    os.close(fd)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    return tmp_path


def _calculate_score(tests, results):
    """
    results – список bool (True = тест пройден)
    Если у тестов есть поле 'score', суммируем баллы пройденных.
    Иначе делим 100 поровну на все тесты.
    """
    if any("score" in case for case in tests):
        total = sum(case.get("score", 0) for case in tests)
        earned = sum(
            case.get("score", 0) for case, passed in zip(tests, results) if passed
        )
        return earned, total
    else:
        """Равномерное распределение"""
        per_test = 100.0 / len(tests)
        earned = per_test * sum(1 for p in results if p)
        return earned, 100.0


"""ФУНКЦИИ ЗАПУСКА ПО ЯЗЫКАМ"""


def _execute_and_check(runner_cmd, tests, language_name):
    passed_list = []
    details = []
    for i, case in enumerate(tests, 1):
        try:
            proc = subprocess.run(
                runner_cmd,
                input=case["input"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            stdout = proc.stdout.strip()
            expected = case["expected"]
            ok = proc.returncode == 0 and stdout == expected
            passed_list.append(ok)
            if not ok:
                details.append(
                    f"Тест {i} провален: ввод={case['input'].strip()}, "
                    f"ожидалось={expected}, получено={stdout or proc.stderr}"
                )
        except subprocess.TimeoutExpired:
            passed_list.append(False)
            details.append(f"Тест {i} превысил время выполнения")
        except Exception as e:
            passed_list.append(False)
            details.append(f"Тест {i} ошибка запуска: {str(e)}")

    if all(passed_list):
        feedback = "Все тесты пройдены!"
    else:
        feedback = "\n".join(details)

    earned, total = _calculate_score(tests, passed_list)
    return {"passed": all(passed_list), "score": round(earned, 1), "feedback": feedback}


def run_python(file_path, tests):
    return _execute_and_check(["python3", file_path], tests, "Python")


def run_cpp(file_path, tests):
    cpp_path = _to_extension(file_path, "cpp")
    executable = tempfile.mktemp(suffix=".out")
    try:
        comp = subprocess.run(
            ["g++", "-std=c++17", "-O2", cpp_path, "-o", executable],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if comp.returncode != 0:
            return {
                "passed": False,
                "score": 0,
                "feedback": f"Ошибка компиляции:\n{comp.stderr}",
            }
        result = _execute_and_check([executable], tests, "C++")
        return result
    finally:
        os.unlink(cpp_path)
        if os.path.exists(executable):
            os.unlink(executable)


def run_javascript(file_path, tests):
    return _execute_and_check(["node", file_path], tests, "JavaScript")


"""ТОЧКА ВХОДА"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"passed": False, "score": 0, "feedback": "Не передан файл с кодом"}
            )
        )
        sys.exit(1)

    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) >= 3 else "python"

    if language == "python":
        result = run_python(file_path, test_cases)
    elif language == "cpp":
        result = run_cpp(file_path, test_cases)
    elif language == "javascript":
        result = run_javascript(file_path, test_cases)
    else:
        result = {
            "passed": False,
            "score": 0,
            "feedback": f"Неподдерживаемый язык: {language}",
        }

    print(json.dumps(result))
