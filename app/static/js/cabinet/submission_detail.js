(function () {
  // ---------- Копирование кода ----------
  function copySolution() {
    const textarea = document.getElementById("submission-code");
    if (!textarea) return;
    let textToCopy = "";
    if (
      textarea.nextElementSibling &&
      textarea.nextElementSibling.classList.contains("CodeMirror")
    ) {
      textToCopy = textarea.nextElementSibling.CodeMirror.getValue();
    } else {
      textToCopy = textarea.value || textarea.textContent || "";
    }
    navigator.clipboard
      .writeText(textToCopy)
      .then(() => {
        const btn = document.querySelector(".btn-copy");
        if (btn) {
          btn.innerHTML = "✅ Скопировано";
          btn.classList.replace("btn-outline-primary", "btn-success");
          setTimeout(() => {
            btn.innerHTML = "📋 Копировать";
            btn.classList.replace("btn-success", "btn-outline-primary");
          }, 2000);
        }
      })
      .catch(() => {
        const temp = document.createElement("textarea");
        temp.value = textToCopy;
        document.body.appendChild(temp);
        temp.select();
        document.execCommand("copy");
        document.body.removeChild(temp);
        alert("Код скопирован");
      });
  }

  // ---------- Инициализация CodeMirror ----------
  function getMode(lang) {
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
    const textarea = document.getElementById("submission-code");
    if (!textarea) return;
    if (
      textarea.nextElementSibling &&
      textarea.nextElementSibling.classList.contains("CodeMirror")
    )
      return;

    const modeName = "{{ submission.language }}" || "python";
    const editor = CodeMirror.fromTextArea(textarea, {
      lineNumbers: true,
      mode: getMode(modeName),
      theme: "dracula",
      readOnly: true,
      lineWrapping: true,
      indentUnit: 4,
      matchBrackets: true,
      styleActiveLine: false,
      viewportMargin: Infinity,
    });

    setTimeout(() => {
      editor.refresh();
      const scrollInfo = editor.getScrollInfo();
      if (scrollInfo && scrollInfo.height)
        editor.setSize(null, scrollInfo.height);
    }, 10);

    // Кнопка копирования
    const btn = document.querySelector(".btn-copy");
    if (btn) btn.addEventListener("click", copySolution);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initEditor);
  } else {
    initEditor();
  }
})();
