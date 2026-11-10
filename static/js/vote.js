// Oy verme, oyu değiştirme ve geri alma: formları fetch ile gönderir ve kartı yeniden çizer.
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
    card.querySelectorAll(".option-button, .withdraw-form button").forEach(function (button) {
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

  // _poll_options.html'deki yapının aynısını üretir. Bu dosya yalnızca açık anketlerde
  // çalıştığı için seçenekler her zaman oy formudur (oy vermiş kişi oyunu taşıyabilir).
  function renderOptions(card, data) {
    var list = card.querySelector(".poll-options");
    var showResults = data.show_results !== false;
    var previousWidths = {};
    list.querySelectorAll(".option-button").forEach(function (button) {
      var bar = button.querySelector(".option-bar");
      if (bar) previousWidths[button.dataset.optionId] = bar.style.width;
    });

    list.classList.toggle("show-results", showResults);
    list.innerHTML = "";

    var bars = [];
    data.options.forEach(function (option, i) {
      var item = el("li", "poll-option");
      item.dataset.index = i + 1;
      var form = el("form", "vote-form");
      form.method = "post";
      form.action = list.dataset.voteUrl;
      var input = el("input");
      input.type = "hidden";
      input.name = "option_id";
      input.value = option.id;
      form.appendChild(input);

      var button = el("button", "option-button");
      button.type = "submit";
      button.dataset.optionId = option.id;
      var isChoice = option.id === data.voted_option_id;

      if (showResults) {
        var bar = el("span", "option-bar");
        bar.style.width = reduceMotion ? option.percent + "%" : (previousWidths[option.id] || "0%");
        button.appendChild(bar);
        bars.push([bar, option.percent]);
      }
      button.appendChild(el("span", "option-text", option.text));
      if (isChoice) {
        item.classList.add("is-choice");
        button.setAttribute("aria-pressed", "true");
        var check = el("span", "option-check", "✓");
        check.setAttribute("aria-label", "Senin seçimin");
        button.appendChild(check);
      }
      if (showResults) {
        button.appendChild(el("span", "option-stats", formatPercent(option.percent) + " · " + option.votes + " oy"));
      }
      form.appendChild(button);
      item.appendChild(form);
      list.appendChild(item);
    });

    renderVoteActions(card, list, data.voted_option_id);

    var total = card.querySelector(".total-count");
    if (total) total.textContent = data.total_votes;

    if (!reduceMotion && bars.length) {
      // Çubukları önceki genişlikten (ilk oyda 0'dan) hedef yüzdeye kaydır (geçişi CSS yapar).
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          bars.forEach(function (pair) { pair[0].style.width = pair[1] + "%"; });
        });
      });
    }
  }

  // "Fikrin mi değişti?" satırı: yalnızca kişinin oyu varken görünür.
  function renderVoteActions(card, list, votedOptionId) {
    var actions = card.querySelector(".vote-actions");
    if (!votedOptionId) {
      if (actions) actions.remove();
      return;
    }
    if (actions) return;
    actions = el("div", "vote-actions");
    actions.appendChild(el("span", "vote-hint", "Fikrin mi değişti? Başka seçeneğe dokun."));
    var form = el("form", "withdraw-form");
    form.method = "post";
    form.action = list.dataset.withdrawUrl;
    var button = el("button", "link-button", "Oyumu geri al");
    button.type = "submit";
    form.appendChild(button);
    actions.appendChild(form);
    list.insertAdjacentElement("afterend", actions);
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.classList) return;
    var isVote = form.classList.contains("vote-form");
    var isWithdraw = form.classList.contains("withdraw-form");
    if (!isVote && !isWithdraw) return;
    var card = form.closest("[data-poll-id]");
    if (!card) return;
    event.preventDefault();
    if (card.getAttribute("aria-busy") === "true") return;

    var errorBox = card.querySelector(".vote-error");
    if (errorBox) errorBox.hidden = true;
    var body = new FormData(form);
    setLocked(card, true);

    fetch(form.action, {
      method: "POST",
      body: body,
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
          renderOptions(card, data);
          card.setAttribute("aria-busy", "false");
          if (window.showToast && data.message) {
            window.showToast(data.message, isWithdraw ? "info" : "success");
          }
        } else {
          setLocked(card, false);
          showError(card, (data && data.error) || "İşlem yapılamadı, tekrar dene.");
        }
      })
      .catch(function () {
        setLocked(card, false);
        showError(card, "Bağlantı hatası, tekrar dene.");
      });
  });
})();
