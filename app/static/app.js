const form = document.querySelector("#shipment-form");
const shipmentList = document.querySelector("#shipment-list");
const shipmentCount = document.querySelector("#shipment-count");
const notice = document.querySelector("#notice");

const stages = [
  ["created", "Создано"],
  ["accepted", "Принято курьерской службой"],
  ["in_transit", "В пути"],
  ["delivered", "Доставлено"],
  ["archived", "Передано в архив"],
];

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.toggle("notice-error", isError);
  notice.hidden = false;
  window.setTimeout(() => { notice.hidden = true; }, 3500);
}

function element(tagName, className, text) {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderTimeline(status) {
  const currentIndex = stages.findIndex(([value]) => value === status);
  const timeline = element("ol", "timeline");
  stages.forEach(([value, label], index) => {
    const item = element("li", `timeline-step ${index <= currentIndex ? "is-complete" : ""}`);
    item.append(element("span", "timeline-dot"), element("span", "timeline-label", label));
    timeline.append(item);
  });
  return timeline;
}

function renderShipment(shipment) {
  const card = element("article", "shipment-card");
  const heading = element("div", "shipment-card-heading");
  const id = element("p", "shipment-id", shipment.id);
  const badge = element("span", "status-badge", shipment.statusLabel);
  heading.append(id, badge);

  const route = element("p", "route");
  route.append(element("span", "route-place", shipment.origin), element("span", "route-arrow", "->"), element("span", "route-place", shipment.destination));
  const recipient = element("p", "recipient", `Получатель: ${shipment.recipient}`);
  card.append(heading, route, recipient, renderTimeline(shipment.status));

  if (shipment.flag) {
    const receipt = element("section", "archive-receipt");
    receipt.append(
      element("p", "eyebrow", "АРХИВНАЯ КВИТАНЦИЯ"),
      element("h3", "", "Доставка завершена"),
      element("p", "receipt-label", "Контрольный код"),
      element("code", "flag", shipment.flag),
    );
    card.append(receipt);
  }
  return card;
}

function renderShipments(shipments) {
  shipmentCount.textContent = String(shipments.length);
  shipmentList.replaceChildren();
  if (!shipments.length) {
    const empty = element("div", "empty-state");
    empty.append(element("span", "empty-mark", "SHP"), element("p", "", "Создайте первую тестовую отправку, чтобы начать отслеживание."));
    shipmentList.append(empty);
    return;
  }
  shipments.forEach((shipment) => shipmentList.append(renderShipment(shipment)));
}

async function loadShipments() {
  const response = await fetch("/api/shipments");
  if (!response.ok) throw new Error("Не удалось загрузить отправления.");
  const { shipments } = await response.json();
  renderShipments(shipments);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = form.querySelector("button[type=submit]");
  submitButton.disabled = true;
  try {
    const data = Object.fromEntries(new FormData(form));
    const response = await fetch("/api/shipments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Не удалось создать отправление.");
    form.reset();
    form.elements.origin.value = "Офис Москва";
    form.elements.destination.value = "Офис Санкт-Петербург";
    await loadShipments();
    showNotice("Отправление создано.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    submitButton.disabled = false;
  }
});

loadShipments().catch((error) => showNotice(error.message, true));
window.setInterval(() => loadShipments().catch(() => {}), 8000);