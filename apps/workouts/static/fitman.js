(function () {
  var activeAiSubmitter = null;

  function preserveSubmitterValue(form, button) {
    if (!button.name) {
      return;
    }
    var marker = "ai-submit-" + button.name;
    if (form.querySelector('input[type="hidden"][data-submit-marker="' + marker + '"]')) {
      return;
    }
    var input = document.createElement("input");
    input.type = "hidden";
    input.name = button.name;
    input.value = button.value || "1";
    input.dataset.submitMarker = marker;
    form.appendChild(input);
  }

  function setLoading(button) {
    var label = button.dataset.loadingText || "Working...";
    var spinner = document.createElement("span");
    var text = document.createElement("span");

    spinner.className = "fm-btn-spinner";
    spinner.setAttribute("aria-hidden", "true");
    text.textContent = label;

    button.replaceChildren(spinner, text);
    button.classList.add("is-loading");
    button.setAttribute("aria-busy", "true");
    button.disabled = true;
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-ai-submit]");
    if (button) {
      activeAiSubmitter = button;
      window.setTimeout(function () {
        if (activeAiSubmitter === button) {
          activeAiSubmitter = null;
        }
      }, 0);
    }
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    var button = event.submitter || activeAiSubmitter;

    if (!button || !button.matches("[data-ai-submit]") || !form.contains(button)) {
      return;
    }

    preserveSubmitterValue(form, button);
    setLoading(button);
    activeAiSubmitter = null;
  });
})();
