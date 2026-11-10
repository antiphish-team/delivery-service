const supportForm = document.querySelector("#support-form");
const supportNotice = document.querySelector("#support-notice");

function showSupportNotice(message, isError = false) {
  supportNotice.textContent = message;
  supportNotice.classList.toggle("is-error", isError);
  supportNotice.hidden = false;
}

supportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = supportForm.querySelector("button[type=submit]");
  submitButton.disabled = true;
  try {
    const response = await fetch("/api/support-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(supportForm))),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Не удалось отправить обращение.");
    supportForm.reset();
    showSupportNotice(`Обращение ${payload.ticketId} отправлено.`);
  } catch (error) {
    showSupportNotice(error.message, true);
  } finally {
    submitButton.disabled = false;
  }
});