function copySolution() {
  const codeArea = document.getElementById("submission-code");
  if (!codeArea) return;

  // Получаем текст либо из CodeMirror (если он уже инициализирован), либо из textarea
  let textToCopy = "";
  if (
    codeArea.nextElementSibling &&
    codeArea.nextElementSibling.classList.contains("CodeMirror")
  ) {
    const cm = codeArea.nextElementSibling.CodeMirror;
    textToCopy = cm.getValue();
  } else {
    textToCopy = codeArea.value || codeArea.textContent || "";
  }

  navigator.clipboard
    .writeText(textToCopy)
    .then(() => {
      // Показываем краткое уведомление
      const btn = document.querySelector(".btn-outline-primary");
      const originalHTML = btn.innerHTML;
      btn.innerHTML = "✅ Скопировано";
      btn.classList.remove("btn-outline-primary");
      btn.classList.add("btn-success");
      setTimeout(() => {
        btn.innerHTML = originalHTML;
        btn.classList.remove("btn-success");
        btn.classList.add("btn-outline-primary");
      }, 2000);
    })
    .catch((err) => {
      // Fallback для старых браузеров
      const tempTextarea = document.createElement("textarea");
      tempTextarea.value = textToCopy;
      document.body.appendChild(tempTextarea);
      tempTextarea.select();
      document.execCommand("copy");
      document.body.removeChild(tempTextarea);
      alert("Код скопирован в буфер обмена");
    });
}

document.addEventListener("DOMContentLoaded", function () {
  var codeArea = document.getElementById("submission-code");
  if (codeArea) {
    var editor = CodeMirror.fromTextArea(codeArea, {
      lineNumbers: true,
      mode: "{{ submission.language }}", // передайте язык из контекста (python, cpp, javascript)
      theme: "dracula",
      readOnly: true, // главное — запрещаем редактирование
      lineWrapping: true, // перенос длинных строк
      indentUnit: 4,
      matchBrackets: true,
      styleActiveLine: false, // для readOnly можно отключить
      viewportMargin: Infinity,
    });
    // Опционально: установить высоту по содержимому
    editor.setSize(null, "auto");
  }
});
