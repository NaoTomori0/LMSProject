// 1. Авто-высота для обычных textarea
function autoResizeTextarea(textarea) {
  if (!textarea) return;
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + 2 + "px";
}
function initAutoResize() {
  document
    .querySelectorAll("textarea.auto-resize")
    .forEach(function (textarea) {
      autoResizeTextarea(textarea);
      textarea.addEventListener("input", function () {
        autoResizeTextarea(this);
      });
    });
}

// 2. Подсветка и автодополнение для CodeMirror
function getModeFromLanguage(lang) {
  switch (lang) {
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

// Ключевые слова для разных языков
var keywords = {
  python: [
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
    "print",
    "len",
    "range",
    "str",
    "int",
    "float",
    "list",
    "dict",
    "set",
    "tuple",
    "open",
    "input",
    "abs",
    "round",
    "sum",
    "min",
    "max",
  ],
  cpp: [
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "int",
    "long",
    "register",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "class",
    "namespace",
    "template",
    "public",
    "private",
    "protected",
    "virtual",
    "include",
    "iostream",
    "vector",
    "string",
    "cout",
    "cin",
  ],
  javascript: [
    "abstract",
    "arguments",
    "boolean",
    "break",
    "byte",
    "case",
    "catch",
    "char",
    "class",
    "const",
    "continue",
    "debugger",
    "default",
    "delete",
    "do",
    "double",
    "else",
    "enum",
    "eval",
    "export",
    "extends",
    "false",
    "final",
    "finally",
    "float",
    "for",
    "function",
    "goto",
    "if",
    "implements",
    "import",
    "in",
    "instanceof",
    "int",
    "interface",
    "let",
    "long",
    "native",
    "new",
    "null",
    "package",
    "private",
    "protected",
    "public",
    "return",
    "short",
    "static",
    "super",
    "switch",
    "synchronized",
    "this",
    "throw",
    "throws",
    "transient",
    "true",
    "try",
    "typeof",
    "var",
    "void",
    "volatile",
    "while",
    "with",
    "yield",
    "console",
    "document",
    "window",
    "alert",
    "require",
    "process",
  ],
  java: [
    "abstract",
    "assert",
    "boolean",
    "break",
    "byte",
    "case",
    "catch",
    "char",
    "class",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extends",
    "final",
    "finally",
    "float",
    "for",
    "goto",
    "if",
    "implements",
    "import",
    "instanceof",
    "int",
    "interface",
    "long",
    "native",
    "new",
    "package",
    "private",
    "protected",
    "public",
    "return",
    "short",
    "static",
    "strictfp",
    "super",
    "switch",
    "synchronized",
    "this",
    "throw",
    "throws",
    "transient",
    "try",
    "void",
    "volatile",
    "while",
    "String",
    "System",
    "public",
    "void",
    "main",
  ],
  bash: [
    "alias",
    "bind",
    "builtin",
    "caller",
    "case",
    "command",
    "compgen",
    "complete",
    "dirs",
    "disown",
    "echo",
    "enable",
    "eval",
    "exec",
    "exit",
    "export",
    "false",
    "fc",
    "fg",
    "for",
    "getopts",
    "hash",
    "help",
    "history",
    "if",
    "jobs",
    "kill",
    "let",
    "local",
    "logout",
    "popd",
    "printf",
    "pushd",
    "pwd",
    "read",
    "return",
    "set",
    "shift",
    "shopt",
    "source",
    "suspend",
    "test",
    "times",
    "trap",
    "true",
    "type",
    "ulimit",
    "umask",
    "unalias",
    "unset",
    "until",
    "variables",
    "wait",
    "while",
  ],
};

function customHint(cm) {
  var cur = cm.getCursor();
  var token = cm.getTokenAt(cur);
  var word = token.string;
  var mode = cm.getOption("mode");
  var list = [];

  // Собираем слова из документа
  var docWords = {};
  cm.eachLine(function (line) {
    var words = line.text.match(/\b[a-zA-Z_][a-zA-Z0-9_]*\b/g);
    if (words)
      words.forEach(function (w) {
        docWords[w] = true;
      });
  });
  var docList = Object.keys(docWords);

  if (mode === "python") {
    var combined = keywords.python.concat(docList);
    list = combined.filter(function (item) {
      return item.startsWith(word);
    });
  } else if (mode === "text/x-c++src") {
    var combined = keywords.cpp.concat(docList);
    list = combined.filter(function (item) {
      return item.startsWith(word);
    });
  } else if (mode === "text/x-java") {
    var combined = keywords.java.concat(docList);
    list = combined.filter(function (item) {
      return item.startsWith(word);
    });
  } else if (mode === "shell") {
    var combined = keywords.bash.concat(docList);
    list = combined.filter(function (item) {
      return item.startsWith(word);
    });
  } else {
    // Для javascript и других используем встроенный хинт или anyword
    if (
      mode === "javascript" &&
      typeof CodeMirror.hint.javascript !== "undefined"
    ) {
      var jsHint = CodeMirror.hint.javascript(cm);
      if (jsHint) list = jsHint.list;
    } else {
      var anyHint = CodeMirror.hint.anyword(cm);
      if (anyHint) list = anyHint.list;
    }
  }

  return {
    list: list,
    from: CodeMirror.Pos(cur.line, token.start),
    to: CodeMirror.Pos(cur.line, token.end),
  };
}

function initCodeMirror() {
  var textarea = document.getElementById("script_body");
  if (!textarea) return;

  if (
    textarea.nextElementSibling &&
    textarea.nextElementSibling.classList &&
    textarea.nextElementSibling.classList.contains("CodeMirror")
  ) {
    return;
  }

  var initialLang = document.getElementById("language").value;
  var initialMode = getModeFromLanguage(initialLang);

  var editor = CodeMirror.fromTextArea(textarea, {
    lineNumbers: true,
    mode: initialMode,
    theme: "dracula",
    indentUnit: 4,
    matchBrackets: true,
    autoCloseBrackets: true,
    styleActiveLine: true,
    lineWrapping: true,
    viewportMargin: Infinity,
    extraKeys: {
      "Ctrl-Space": function (cm) {
        cm.showHint({ hint: customHint, completeSingle: false });
      },
    },
  });

  setTimeout(function () {
    editor.refresh();
  }, 10);

  editor.on("inputRead", function (cm, change) {
    if (change.text.length === 1 && /[a-zA-Z0-9_]$/.test(change.text[0])) {
      cm.showHint({ hint: customHint, completeSingle: false });
    }
  });

  var langSelect = document.getElementById("language");
  langSelect.addEventListener("change", function () {
    var newMode = getModeFromLanguage(this.value);
    editor.setOption("mode", newMode);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initAutoResize();
    initCodeMirror();
  });
} else {
  initAutoResize();
  initCodeMirror();
}
