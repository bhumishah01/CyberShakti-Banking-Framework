(() => {
  const forms = document.querySelectorAll(".lang-form");
  if (!forms.length) return;

  forms.forEach((form) => {
    const select = form.querySelector("select[name='lang']");
    if (!select) return;

    select.addEventListener("change", (event) => {
      event.preventDefault();
      const nextLang = String(select.value || "").trim();
      if (!nextLang) return;

      const url = new URL(window.location.href);
      url.searchParams.set("lang", nextLang);
      window.location.href = url.toString();
    });
  });
})();
