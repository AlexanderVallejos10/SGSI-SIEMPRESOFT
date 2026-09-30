// Muestra solo los campos que exige la opción de tratamiento elegida (reunión con Karim).
(function () {
  "use strict";
  var select = document.getElementById("id_option");
  if (!select) return;

  var byOption = {
    "1": ["control"],
    "2": ["third_party", "third_party_responsibilities", "contract_reference", "evidence"],
    "3": ["avoidance_method"],
    "4": ["acceptance_justification", "approver", "approved_at"]
  };
  var all = [];
  Object.keys(byOption).forEach(function (key) { all = all.concat(byOption[key]); });

  function box(name) {
    var input = document.getElementById("id_" + name);
    return input ? input.closest(".form-field") : null;
  }

  function sync() {
    var shown = byOption[(select.value || "").charAt(0)] || [];
    all.forEach(function (name) {
      var el = box(name);
      if (!el) return;
      var visible = shown.indexOf(name) !== -1;
      var hasError = el.querySelector(".field-error");
      el.hidden = !visible && !hasError;
      var label = el.querySelector("label");
      var mark = label && label.querySelector(".req-mark");
      if (label && !mark) {
        mark = document.createElement("span");
        mark.className = "req-mark";
        mark.textContent = " *";
        mark.style.color = "#a8551a";
        label.appendChild(mark);
      }
      if (mark) mark.hidden = !visible || name === "evidence" || name === "approver" || name === "approved_at";
    });
  }

  select.addEventListener("change", sync);
  sync();
})();
