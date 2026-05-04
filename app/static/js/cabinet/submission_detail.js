function copySolution() {
  const codeArea = document.getElementById("submission-code");
  if (!codeArea) return;

  let textToCopy = "";
  // Проверяем, инициализирован ли CodeMirror
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
      const btn = document.querySelector(".btn-outline-primary");
      if (!btn) return;
      btn.innerHTML = "✅ Скопировано";
      btn.classList.remove("btn-outline-primary");
      btn.classList.add("btn-success");
      setTimeout(() => {
        btn.innerHTML = "📋 Копировать";
        btn.classList.remove("btn-success");
        btn.classList.add("btn-outline-primary");
      }, 2000);
    })
    .catch((err) => {
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

  document.addEventListener("DOMContentLoaded", function () {
    const textarea = document.getElementById("submission-code");
    if (!textarea) return;

    // Защита от повторной инициализации
    if (
      textarea.nextElementSibling &&
      textarea.nextElementSibling.classList.contains("CodeMirror")
    ) {
      return;
    }

    const lang = textarea.getAttribute("data-language") || "python";
    const mode = getCodeMirrorMode(lang);

    const editor = CodeMirror.fromTextArea(textarea, {
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

    // Авто‑высота
    setTimeout(function () {
      editor.refresh();
      editor.setSize(null, editor.getScrollInfo().height);
    }, 10);
  });
})();
