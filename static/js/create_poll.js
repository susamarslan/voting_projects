// Anket oluşturma formu: seçenek ekle/sil ve gönderim öncesi doğrulama.
// JS kapalıysa sunucu 5 input gösterir ve doğrulamayı tek başına yapar.
(function () {
  "use strict";

  var MIN_OPTIONS = 2;
  var MAX_OPTIONS = 5;

  var form = document.getElementById("poll-form");
  var list = document.getElementById("option-list");
  var addButton = document.getElementById("add-option");
  var errorBox = document.getElementById("option-errors");
  if (!form || !list || !addButton || !errorBox) return;

  var pool = []; // DOM'dan çıkarılmış, tekrar kullanılabilecek satırlar

  function rows() {
    return Array.prototype.slice.call(list.querySelectorAll(".option-row"));
  }

  function inputOf(row) {
    return row.querySelector("input[name='options']");
  }

  function renumber() {
    var current = rows();
    current.forEach(function (row, i) {
      var n = i + 1;
      var input = inputOf(row);
      var label = row.querySelector("label");
      var remove = row.querySelector(".remove-option");
      row.dataset.index = n;
      input.id = "option-" + n;
      input.placeholder = "Seçenek " + n;
      label.htmlFor = input.id;
      label.textContent = "Seçenek " + n;
      remove.setAttribute("aria-label", "Seçenek " + n + "'i kaldır");
      remove.hidden = current.length <= MIN_OPTIONS;
    });
    addButton.hidden = current.length >= MAX_OPTIONS;
  }

  function removeRow(row) {
    if (rows().length <= MIN_OPTIONS) return;
    inputOf(row).value = "";
    list.removeChild(row);
    pool.push(row);
    renumber();
    var remaining = rows();
    inputOf(remaining[remaining.length - 1]).focus();
  }

  function addRow() {
    if (rows().length >= MAX_OPTIONS || pool.length === 0) return;
    var row = pool.shift();
    list.appendChild(row);
    renumber();
    inputOf(row).focus();
  }

  function showErrors(container, messages) {
    container.innerHTML = "";
    messages.forEach(function (text) {
      var p = document.createElement("p");
      p.className = "error";
      p.textContent = text;
      container.appendChild(p);
    });
    container.hidden = messages.length === 0;
  }

  function validateQuestion() {
    var input = form.querySelector("[name='question']");
    if (!input) return true;
    var field = input.closest(".field") || input.parentNode;
    var old = field.querySelector(".js-error");
    if (old) old.remove();

    var length = input.value.trim().length;
    var message = "";
    if (length === 0) message = "Soru zorunludur.";
    else if (length < 5) message = "Soru en az 5 karakter olmalı.";
    else if (length > 200) message = "Soru en fazla 200 karakter olabilir.";
    if (!message) return true;

    var p = document.createElement("p");
    p.className = "error js-error";
    p.textContent = message;
    field.appendChild(p);
    return false;
  }

  function validateOptions() {
    var values = rows()
      .map(function (row) { return inputOf(row).value.trim(); })
      .filter(function (v) { return v.length > 0; });

    var errors = [];
    if (values.length < MIN_OPTIONS) errors.push("En az " + MIN_OPTIONS + " seçenek girmelisin.");
    if (values.length > MAX_OPTIONS) errors.push("En fazla " + MAX_OPTIONS + " seçenek girebilirsin.");

    var seen = {};
    var duplicate = values.some(function (v) {
      var key = v.toLowerCase();
      if (seen[key]) return true;
      seen[key] = true;
      return false;
    });
    if (duplicate) errors.push("Aynı seçeneği birden fazla kez yazamazsın.");

    showErrors(errorBox, errors);
    return errors.length === 0;
  }

  // Başlangıç: dolu satırları (en az 2) göster, kalan boş satırları havuza al.
  var initial = rows();
  var filledCount = initial.filter(function (row) { return inputOf(row).value.trim(); }).length;
  var visibleCount = Math.max(MIN_OPTIONS, Math.min(filledCount, MAX_OPTIONS));
  // Boş satırları sona taşı ki dolu olanlar görünür kalsın.
  initial
    .filter(function (row) { return !inputOf(row).value.trim(); })
    .forEach(function (row) { list.appendChild(row); });
  rows().slice(visibleCount).forEach(function (row) {
    list.removeChild(row);
    pool.push(row);
  });

  rows().concat(pool).forEach(function (row) {
    row.querySelector(".remove-option").addEventListener("click", function () {
      removeRow(row);
    });
  });
  addButton.addEventListener("click", addRow);

  form.addEventListener("submit", function (event) {
    var questionOk = validateQuestion();
    var optionsOk = validateOptions();
    if (!questionOk || !optionsOk) event.preventDefault();
  });

  renumber();
})();
