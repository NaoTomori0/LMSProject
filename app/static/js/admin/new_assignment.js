// ---------- Авто-высота для всех textarea с классом auto-resize ----------
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
const checkType = document.getElementById("check_type");
const autoDiv = document.getElementById("auto-script");
const quizSection = document.getElementById("quiz-section");

function toggleTypeBlocks() {
  autoDiv.style.display = checkType.value === "auto" ? "block" : "none";
  quizSection.style.display = checkType.value === "quiz" ? "block" : "none";
}
checkType.addEventListener("change", toggleTypeBlocks);
window.addEventListener("DOMContentLoaded", toggleTypeBlocks);

const radioPublic = document.getElementById("vis-public");
const radioAuth = document.getElementById("vis-auth");
const radioGroup = document.getElementById("vis-group");
const groupDiv = document.getElementById("group-select");

function toggleGroupSelect() {
  groupDiv.style.display = radioGroup.checked ? "block" : "none";
}
radioPublic.addEventListener("change", toggleGroupSelect);
radioAuth.addEventListener("change", toggleGroupSelect);
radioGroup.addEventListener("change", toggleGroupSelect);
window.addEventListener("DOMContentLoaded", toggleGroupSelect);

// ---------- Конструктор вопросов ----------
let questionIndex = 0;

function updateOptionsForQuestion(card) {
  const typeSelect = card.querySelector('select[name="question_type"]');
  if (!typeSelect) return;
  const currentType = typeSelect.value;
  const container = card.querySelector('[class*="options-container-"]');
  if (!container) return;
  const qIdxMatch = container.className.match(/options-container-(\d+)/);
  if (!qIdxMatch) return;
  const qIdx = qIdxMatch[1];
  const optionGroups = container.querySelectorAll(".input-group");
  optionGroups.forEach((group, optIdx) => {
    const input = group.querySelector(
      "input[type=radio], input[type=checkbox]",
    );
    if (!input) return;
    const newType = currentType === "single" ? "radio" : "checkbox";
    const newName =
      "option_correct_" + qIdx + (newType === "checkbox" ? "[]" : "");
    input.type = newType;
    input.name = newName;
    if (newType === "radio") input.checked = false;
  });
}

function addQuestion() {
  const container = document.getElementById("questions-container");
  const idx = questionIndex++;
  const card = document.createElement("div");
  card.className = "card mb-3";
  card.innerHTML = `
            <div class="card-body">
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
  const typeSelect = card.querySelector('select[name="question_type"]');
  if (typeSelect) {
    typeSelect.addEventListener("change", () => updateOptionsForQuestion(card));
  }
  container.appendChild(card);
}

function addOption(btn, qIdx) {
  const card = btn.closest(".card");
  const typeSelect = card.querySelector('select[name="question_type"]');
  const currentType = typeSelect ? typeSelect.value : "single";
  const container = card.querySelector(`.options-container-${qIdx}`);
  const optIdx = container.children.length;
  const div = document.createElement("div");
  div.className = "input-group mb-1";
  const inputType = currentType === "single" ? "radio" : "checkbox";
  const inputName =
    "option_correct_" + qIdx + (inputType === "checkbox" ? "[]" : "");
  div.innerHTML = `
            <input type="text" class="form-control" name="option_text_${qIdx}[]" placeholder="Текст варианта">
            <div class="input-group-text">
                <input type="${inputType}" name="${inputName}" value="${optIdx}">
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.input-group').remove()">×</button>
        `;
  container.appendChild(div);
}

// Запуск авто-высоты после загрузки страницы
document.addEventListener("DOMContentLoaded", function () {
  initAutoResize();
  // Если есть уже созданные вопросы в DOM (при редактировании), они обработаются, но здесь новый шаблон – пустой
});
