document.addEventListener("DOMContentLoaded", function () {
  // ----- Списки ключевых слов -----
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
  };

  // ----- Пользовательская функция подсказок -----
  function customHint(cm, lang) {
    var cur = cm.getCursor();
    var token = cm.getTokenAt(cur);
    var word = token.string;
    var list = [];

    // Собираем слова из текущего документа
    var docWords = {};
    cm.eachLine(function (line) {
      var words = line.text.match(/\b[a-zA-Z_][a-zA-Z0-9_]*\b/g);
      if (words)
        words.forEach(function (w) {
          docWords[w] = true;
        });
    });
    var docList = Object.keys(docWords);

    // Объединяем с ключевыми словами языка
    var langKeywords = keywords[lang] || [];
    var combined = langKeywords.concat(docList);
    list = combined.filter(function (item) {
      return item.startsWith(word);
    });

    return {
      list: list,
      from: CodeMirror.Pos(cur.line, token.start),
      to: CodeMirror.Pos(cur.line, token.end),
    };
  }

  // ----- Выбор подсказчика в зависимости от режима -----
  function getHint(cm) {
    var mode = cm.getOption("mode");
    if (mode === "python") {
      return function (cm) {
        return customHint(cm, "python");
      };
    } else if (mode === "text/x-c++src") {
      return function (cm) {
        return customHint(cm, "cpp");
      };
    } else if (mode === "text/x-java") {
      return function (cm) {
        return customHint(cm, "java");
      };
    } else {
      // Для JavaScript оставляем нативный хинт (объекты, методы и т.д.)
      return CodeMirror.hint.javascript;
    }
  }

  // ----- Инициализация редактора -----
  var editor = CodeMirror.fromTextArea(document.getElementById("editor"), {
    lineNumbers: true,
    mode: "python",
    theme: "dracula",
    indentUnit: 4,
    matchBrackets: true,
    autoCloseBrackets: true,
    styleActiveLine: true,
    extraKeys: {
      "Ctrl-Space": function (cm) {
        cm.showHint({ hint: getHint(cm), completeSingle: false });
      },
    },
    viewportMargin: Infinity,
  });
  editor.setSize(null, "auto");

  // Автодополнение при вводе букв, цифр, подчёркивания, точки
  editor.on("inputRead", function (cm, change) {
    if (change.text.length === 1 && /[a-zA-Z0-9_.]$/.test(change.text[0])) {
      cm.showHint({ hint: getHint(cm), completeSingle: false });
    }
  });

  // Переключение языка
  var langSelect = document.getElementById("language-select");
  var hiddenLang = document.getElementById("selected-language");

  langSelect.addEventListener("change", function () {
    var val = this.value;
    hiddenLang.value = val;
    var mode = "python";
    if (val === "javascript") mode = "javascript";
    else if (val === "cpp") mode = "text/x-c++src";
    else if (val === "java") mode = "text/x-java";
    editor.setOption("mode", mode);
  });

  hiddenLang.value = langSelect.value;
});
