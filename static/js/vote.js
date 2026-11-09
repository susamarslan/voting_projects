// Oy verme: seçenek formlarını fetch ile gönderir ve kartı sonuç görünümüne çevirir.
// JS kapalıysa formlar normal POST olarak çalışır (sunucu detay sayfasına yönlendirir).
(function () {
  "use strict";

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function formatPercent(value) {
    return "%" + value.toLocaleString("tr-TR", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function setLocked(card, locked) {
    card.querySelectorAll(".option-button").forEach(function (button) {
      button.disabled = locked;
    });
    card.setAttribute("aria-busy", locked ? "true" : "false");
  }

  function showError(card, message) {
    var box = card.querySelector(".vote-error");
    if (!box) return;
    box.textContent = message;
    box.hidden = false;
  }

  // _poll_options.html'deki .option-result yapısının aynısını üretir.
  function renderResults(card, data) {
    var list = card.querySelector(".poll-options");
    list.classList.add("show-results");
    list.innerHTML = "";

    var bars = [];
    data.options.forEach(function (option, i) {
      var item = el("li", "poll-option");
      item.dataset.index = i + 1;
      var row = el("div", "option-result");
      var bar = el("span", "option-bar");
      bar.style.width = reduceMotion ? option.percent + "%" : "0%";
      row.appendChild(bar);
      row.appendChild(el("span", "option-text", option.text));
      if (option.id === data.voted_option_id) {
        item.classList.add("is-choice");
        var check = el("span", "option-check", "✓");
        check.setAttribute("aria-label", "Senin seçimin");
        row.appendChild(check);
      }
      row.appendChild(el("span", "option-stats", formatPercent(option.percent) + " · " + option.votes + " oy"));
      item.appendChild(row);
      list.appendChild(item);
      bars.push([bar, option.percent]);
    });

    var total = card.querySelector(".total-count");
    if (total) total.textContent = data.total_votes;

    if (!reduceMotion) {
      // Çubukları 0'dan hedef yüzdeye doldur (geçişi CSS yapar).
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          bars.forEach(function (pair) { pair[0].style.width = pair[1] + "%"; });
        });
      });
    }
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.classList || !form.classList.contains("vote-form")) return;
    var card = form.closest("[data-poll-id]");
    if (!card) return;
    event.preventDefault();
    if (card.getAttribute("aria-busy") === "true") return;

    var errorBox = card.querySelector(".vote-error");
    if (errorBox) errorBox.hidden = true;
    setLocked(card, true);

    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    })
      .then(function (response) {
        return response.json().catch(function () { return { ok: false }; });
      })
      .then(function (data) {
        if (data && data.ok) {
          renderResults(card, data);
          card.setAttribute("aria-busy", "false");
          if (window.showToast) window.showToast("Oyun kaydedildi 🎉", "success");
        } else {
          setLocked(card, false);
          showError(card, (data && data.error) || "Oy kaydedilemedi, tekrar dene.");
        }
      })
      .catch(function () {
        setLocked(card, false);
        showError(card, "Bağlantı hatası, tekrar dene.");
      });
  });
})();
