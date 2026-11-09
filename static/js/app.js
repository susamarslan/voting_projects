// Genel küçük yardımcılar.
(function () {
  "use strict";

  // data-confirm özniteliği olan formlar gönderilmeden önce onay ister.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    var message = form.getAttribute && form.getAttribute("data-confirm");
    if (message && !window.confirm(message)) event.preventDefault();
  });
})();
