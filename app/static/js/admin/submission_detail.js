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

(function () {
  function getCodeMirrorMode(lang) {
    if (!lang) return "python";
    switch (lang.toLowerCase()) {
      case "javascript":
        return "javascript";
      case "cpp":
        return "text/x-c++src";
      case "java":
        return "text/x-java";
      case "bash":
        return "shell";
      default:
        return "python";
    }
  }

  function initEditor() {
    var textarea = document.getElementById("submission-code");
    if (!textarea) return;

    // Защита от повторной инициализации
    if (
      textarea.nextElementSibling &&
      textarea.nextElementSibling.classList &&
      textarea.nextElementSibling.classList.contains("CodeMirror")
    ) {
      return;
    }

    var modeName = '{{ submission.language | default("python") }}';
    var mode = getCodeMirrorMode(modeName);

    var editor = CodeMirror.fromTextArea(textarea, {
      lineNumbers: true,
      mode: mode,
      theme: "dracula",
      readOnly: true,
      lineWrapping: true,
      indentUnit: 4,
      matchBrackets: true,
      styleActiveLine: false,
      viewportMargin: Infinity,
    });

    // Принудительный пересчёт высоты после рендеринга
    setTimeout(function () {
      editor.refresh();
      var scrollInfo = editor.getScrollInfo();
      if (scrollInfo && scrollInfo.height) {
        editor.setSize(null, scrollInfo.height);
      }
    }, 10);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initEditor);
  } else {
    initEditor();
  }
})();
editor.setSize(null, "auto");
