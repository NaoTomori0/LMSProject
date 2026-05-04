(function () {
  // ---------- Копирование кода решения ----------
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

    const container = document.getElementById("submission-container");
    const modeName =
      (container && container.dataset.language) ||
      (typeof submissionLanguage !== "undefined"
        ? submissionLanguage
        : "python");
    const mode = getMode(modeName);

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

    setTimeout(() => {
      editor.refresh();
      const scrollInfo = editor.getScrollInfo();
      if (scrollInfo && scrollInfo.height)
        editor.setSize(null, scrollInfo.height);
    }, 10);
  }

  // Вешаем обработчик копирования при загрузке
  function bindCopyButton() {
    const btn = document.querySelector(".btn-copy");
    if (btn) btn.addEventListener("click", copySolution);
  }

  // Запуск после загрузки DOM
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initEditor();
      bindCopyButton();
    });
  } else {
    initEditor();
    bindCopyButton();
  }
})();
