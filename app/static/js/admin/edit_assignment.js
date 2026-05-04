// ---------- Авто-высота для textarea ----------
function autoResizeTextarea(textarea) {
  if (!textarea) return;
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + 2 + "px";
}

function initAutoResize() {
  document.querySelectorAll("textarea.auto-resize").forEach((textarea) => {
    autoResizeTextarea(textarea);
    textarea.addEventListener("input", function () {
      autoResizeTextarea(this);
    });
  });
}

// ---------- Переключение блоков ----------
var checkType = document.getElementById("check_type");
var autoDiv = document.getElementById("auto-script");
var quizSection = document.getElementById("quiz-section");
function toggleBlocks() {
  autoDiv.style.display = checkType.value === "auto" ? "block" : "none";
  quizSection.style.display = checkType.value === "quiz" ? "block" : "none";
}
checkType.addEventListener("change", toggleBlocks);
window.addEventListener("DOMContentLoaded", toggleBlocks);

var radioGroup = document.getElementById("vis-group");
var groupDiv = document.getElementById("group-select");
function toggleGroup() {
  groupDiv.style.display = radioGroup.checked ? "block" : "none";
}
document.querySelectorAll('input[name="visibility"]').forEach(function (r) {
  r.addEventListener("change", toggleGroup);
});
window.addEventListener("DOMContentLoaded", toggleGroup);

// ---------- Конструктор вопросов ----------
var questionIndex = parseInt("{{ questions|length }}") || 0;

function updateOptionInputs(card) {
  var typeSelect = card.querySelector('select[name="question_type"]');
  if (!typeSelect) return;
  var currentType = typeSelect.value;
  var container = card.querySelector('[class*="options-container-"]');
  if (!container) return;
  var match = container.className.match(/options-container-(\d+)/);
  if (!match) return;
  var qIdx = match[1];
  var groups = container.querySelectorAll(".input-group");
  groups.forEach(function (group) {
    var input = group.querySelector("input[type=radio], input[type=checkbox]");
    if (!input) return;
    var newType = currentType === "single" ? "radio" : "checkbox";
    input.type = newType;
    input.name =
      "option_correct_" + qIdx + (newType === "checkbox" ? "[]" : "");
    if (newType === "radio") input.checked = false;
  });
}

// Инициализация существующих вопросов
document
  .querySelectorAll("#questions-container .card")
  .forEach(function (card) {
    updateOptionInputs(card);
    var typeSelect = card.querySelector('select[name="question_type"]');
    if (typeSelect) {
      typeSelect.addEventListener("change", function () {
        updateOptionInputs(card);
      });
    }
  });

function addQuestion() {
  var container = document.getElementById("questions-container");
  var idx = questionIndex++;
  var div = document.createElement("div");
  div.className = "card mb-3";
  div.innerHTML = `
            <div class="card-body">
                <input type="hidden" name="question_id_${idx}" value="0">
                <div class="mb-2">
                    <label>Текст вопроса</label>
                    <input type="text" class="form-control" name="question_text" required>
                </div>
                <div class="mb-2">
                    <label>Тип</label>
                    <select class="form-select" name="question_type">
                        <option value="single">Один вариант</option>
                        <option value="multiple">Несколько вариантов</option>
                        <option value="open">Развёрнутый ответ</option>
                    </select>
                </div>
                <div class="mb-2">
                    <label>Баллы за вопрос</label>
                    <input type="number" class="form-control" name="question_score" min="0" step="0.1" value="1.0" required>
                </div>
                <div class="options-container-${idx} mb-2"></div>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="addOption(this, ${idx})">+ Вариант</button>
                <button type="button" class="btn btn-sm btn-danger float-end" onclick="this.closest('.card').remove()">Удалить вопрос</button>
            </div>
        `;
  var typeSelect = div.querySelector('select[name="question_type"]');
  if (typeSelect) {
    typeSelect.addEventListener("change", function () {
      updateOptionInputs(div);
    });
  }
  container.appendChild(div);
}

function addOption(btn, qIdx) {
  var card = btn.closest(".card");
  var typeSelect = card.querySelector('select[name="question_type"]');
  var currentType = typeSelect ? typeSelect.value : "single";
  var container = card.querySelector(".options-container-" + qIdx);
  var optIdx = container.children.length;
  var div = document.createElement("div");
  div.className = "input-group mb-1";
  var inputType = currentType === "single" ? "radio" : "checkbox";
  var name = "option_correct_" + qIdx + (inputType === "checkbox" ? "[]" : "");
  div.innerHTML = `
            <input type="text" class="form-control" name="option_text_${qIdx}[]" placeholder="Текст варианта">
            <div class="input-group-text">
                <input type="${inputType}" name="${name}" value="${optIdx}">
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.input-group').remove()">×</button>
        `;
  container.appendChild(div);
}

// Запуск авто-высоты после полной загрузки страницы (включая существующие вопросы и динамические)
document.addEventListener("DOMContentLoaded", function () {
  initAutoResize();
  // Наблюдатель за динамическими textarea (если появятся в будущем)
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.addedNodes.length) {
        mutation.addedNodes.forEach(function (node) {
          if (
            node.nodeType === 1 &&
            node.matches &&
            node.matches("textarea.auto-resize")
          ) {
            autoResizeTextarea(node);
            node.addEventListener("input", function () {
              autoResizeTextarea(this);
            });
          }
        });
      }
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
});
