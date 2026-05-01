import sys

with open(sys.argv[1]) as f:
    answer = f.read().strip()
# Простейшая проверка: ответ должен содержать слово "Flask"
if "Flask" in answer:
    print('{"passed": true, "score": 10, "feedback": "Верно!"}')
else:
    print('{"passed": false, "score": 0, "feedback": "Не упомянут Flask"}')
