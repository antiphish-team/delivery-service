ALLOWED_TRANSITIONS = {
    "created": "accepted",
    "accepted": "in_transit",
    "in_transit": "delivered",
    "delivered": "archived",
}

STATUS_LABELS = {
    "created": "Создано",
    "accepted": "Принято курьерской службой",
    "in_transit": "В пути",
    "delivered": "Доставлено",
    "archived": "Передано в архив",
}