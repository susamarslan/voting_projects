// Genel küçük yardımcılar: toast bildirimleri, silme onayı, link kopyalama.
(function () {
  "use strict";

  var TOAST_DURATION = 3500;

  function dismiss(toast) {
    if (!toast || toast.classList.contains("is-leaving")) return;
    toast.classList.add("is-leaving");
    setTimeout(function () { toast.remove(); }, 260);
  }

  function arm(toast) {
    var close = toast.querySelector(".toast-close");
    if (close) close.addEventListener("click", function () { dismiss(toast); });
    var timer = setTimeout(function () { dismiss(toast); }, TOAST_DURATION);
    // Fareyle üzerine gelinirken kapanmasın.
    toast.addEventListener("mouseenter", function () { clearTimeout(timer); });
    toast.addEventListener("mouseleave", function () {
      timer = setTimeout(function () { dismiss(toast); }, 1500);
    });
  }

  // Diğer scriptler de kullanabilsin: window.showToast("Mesaj", "success" | "error" | "info")
  window.showToast = function (message, type) {
    var stack = document.getElementById("toast-stack");
    if (!stack) return;
    var toast = document.createElement("div");
    toast.className = "toast toast-" + (type || "info");
    var text = document.createElement("span");
    text.textContent = message;
    var close = document.createElement("button");
    close.type = "button";
    close.className = "toast-close";
    close.setAttribute("aria-label", "Bildirimi kapat");
    close.textContent = "×";
    toast.appendChild(text);
    toast.appendChild(close);
    stack.appendChild(toast);
    arm(toast);
  };

  // Sunucudan gelen (Django messages) toast'ları otomatik kapat.
  document.querySelectorAll("#toast-stack .toast").forEach(arm);

  // data-confirm özniteliği olan formlar gönderilmeden önce onay ister.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    var message = form.getAttribute && form.getAttribute("data-confirm");
    if (message && !window.confirm(message)) event.preventDefault();
  });

  // "Linki kopyala" butonları.
  function fallbackCopy(text) {
    var input = document.createElement("textarea");
    input.value = text;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    input.remove();
    return ok ? Promise.resolve() : Promise.reject();
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-copy-url]");
    if (!button) return;
    var url = button.getAttribute("data-copy-url");
    var copy = navigator.clipboard && window.isSecureContext
      ? navigator.clipboard.writeText(url).catch(function () { return fallbackCopy(url); })
      : fallbackCopy(url);
    copy.then(
      function () { window.showToast("Kopyalandı! 📋", "success"); },
      function () { window.showToast("Kopyalanamadı, adres çubuğundan kopyalayabilirsin.", "error"); }
    );
  });
})();
