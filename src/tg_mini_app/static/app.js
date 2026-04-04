/* global Telegram */

const apiBase = "";

function rub(n) {
  const v = Number(n);
  if (Number.isNaN(v)) return "0 ₽";
  return `${Math.round(v)} ₽`;
}

function byId(id) {
  return document.getElementById(id);
}

async function apiGet(path) {
  const r = await fetch(`${apiBase}${path}`, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`GET ${path} -> ${r.status}`);
  return await r.json();
}

async function apiPost(path, body) {
  const r = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`POST ${path} -> ${r.status}`);
  return await r.json();
}

async function ensureCart() {
  let cartId = localStorage.getItem("cart_id");
  if (!cartId) {
    const cart = await apiPost("/cart", { owner_tg_id: getTgUserId() });
    cartId = cart.id;
    localStorage.setItem("cart_id", cartId);
  }
  return cartId;
}

function getTgUserId() {
  try {
    if (!window.Telegram || !Telegram.WebApp) return null;
    const u = Telegram.WebApp.initDataUnsafe?.user;
    if (!u || !u.id) return null;
    return u.id;
  } catch (_) {
    return null;
  }
}

function getTgUserIdFromInput() {
  const el = byId("tgId");
  if (!el) return null;
  const raw = String(el.value || "").trim();
  if (!raw) return null;
  const v = Number(raw);
  if (!Number.isInteger(v) || v <= 0) return null;
  return v;
}

function setThemeFromTelegram() {
  try {
    if (!window.Telegram || !Telegram.WebApp) return;
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  } catch (_) {
    // no-op: running in browser
  }
}

function renderTabs(categories, activeCategoryId) {
  const tabs = byId("tabs");
  tabs.innerHTML = "";

  const makeTab = (label, id) => {
    const b = document.createElement("button");
    b.className = `tab${id === activeCategoryId ? " is-active" : ""}`;
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", () => {
      localStorage.setItem("active_category_id", String(id));
      window.location.reload();
    });
    return b;
  };

  for (const c of categories) tabs.appendChild(makeTab(c.name, c.id));
}

function renderGrid(products, onAdd) {
  const grid = byId("grid");
  grid.innerHTML = "";

  for (const p of products) {
    const card = document.createElement("div");
    card.className = "card";

    const img = document.createElement("div");
    img.className = "card__img";
    img.textContent = p.image_url ? "" : "Фото позже";
    if (p.image_url) {
      img.style.backgroundImage = `url(${p.image_url})`;
      img.style.backgroundSize = "cover";
      img.style.backgroundPosition = "center";
    }

    const body = document.createElement("div");
    body.className = "card__body";

    const name = document.createElement("div");
    name.className = "card__name";
    name.textContent = p.name;

    const desc = document.createElement("div");
    desc.className = "card__desc";
    desc.textContent = p.description || "";

    const meta = document.createElement("div");
    meta.className = "card__meta";
    const weight = document.createElement("span");
    weight.textContent = p.weight_g ? `${p.weight_g} г` : "";
    const price = document.createElement("span");
    price.className = "card__price";
    price.textContent = rub(p.price);
    meta.appendChild(weight);
    meta.appendChild(price);

    const plus = document.createElement("button");
    plus.className = "plus";
    plus.type = "button";
    plus.textContent = "+";
    plus.addEventListener("click", () => onAdd(p.id));

    body.appendChild(name);
    body.appendChild(desc);
    body.appendChild(meta);

    card.appendChild(img);
    card.appendChild(body);
    card.appendChild(plus);
    grid.appendChild(card);
  }
}

function drawerOpen() {
  byId("drawer").hidden = false;
}
function drawerClose() {
  byId("drawer").hidden = true;
}

function renderCart(cart, onDelta) {
  const el = byId("cartItems");
  el.innerHTML = "";

  if (!cart.items.length) {
    const empty = document.createElement("div");
    empty.className = "hint";
    empty.textContent = "Корзина пуста — добавьте позиции из каталога.";
    el.appendChild(empty);
    return;
  }

  for (const it of cart.items) {
    const row = document.createElement("div");
    row.className = "cart-row";

    const left = document.createElement("div");
    const name = document.createElement("div");
    name.className = "cart-row__name";
    name.textContent = it.name;
    const meta = document.createElement("div");
    meta.className = "cart-row__meta";
    meta.textContent = `${rub(it.price)} • ${rub(it.subtotal)}`;
    left.appendChild(name);
    left.appendChild(meta);

    const qty = document.createElement("div");
    qty.className = "qty";
    const minus = document.createElement("button");
    minus.type = "button";
    minus.textContent = "–";
    minus.addEventListener("click", () => onDelta(it.product_id, -1));
    const val = document.createElement("div");
    val.className = "qty__value";
    val.textContent = String(it.qty);
    const plus = document.createElement("button");
    plus.type = "button";
    plus.textContent = "+";
    plus.addEventListener("click", () => onDelta(it.product_id, 1));
    qty.appendChild(minus);
    qty.appendChild(val);
    qty.appendChild(plus);

    row.appendChild(left);
    row.appendChild(qty);
    el.appendChild(row);
  }
}

async function main() {
  setThemeFromTelegram();

  const [categories, products] = await Promise.all([
    apiGet("/catalog/categories"),
    apiGet("/catalog/products"),
  ]);

  let activeCategoryId = Number(localStorage.getItem("active_category_id") || "");
  if (!activeCategoryId || !categories.some((c) => c.id === activeCategoryId)) {
    activeCategoryId = categories[0]?.id ?? 0;
    if (activeCategoryId) localStorage.setItem("active_category_id", String(activeCategoryId));
  }

  renderTabs(categories, activeCategoryId);

  const tgUserId = getTgUserId();
  if (!tgUserId) {
    const f = byId("tgIdField");
    if (f) f.hidden = false;
    byId("checkoutHint").textContent =
      "Не удалось определить Telegram ID. Для отладки введите его вручную (или откройте Mini App строго через кнопку бота).";
  }

  const cartId = await ensureCart();

  async function refreshCart() {
    const cart = await apiGet(`/cart/${cartId}`);
    byId("cartSum").textContent = rub(cart.total);
    renderCart(cart, async (productId, delta) => {
      const updated = await apiPost(`/cart/${cartId}/items`, { product_id: productId, qty_delta: delta });
      byId("cartSum").textContent = rub(updated.total);
      renderCart(updated, arguments.callee);
    });
    return cart;
  }

  renderGrid(
    products.filter((p) => p.category_id === activeCategoryId),
    async (productId) => {
      await apiPost(`/cart/${cartId}/items`, { product_id: productId, qty_delta: 1 });
      await refreshCart();
    },
  );

  byId("cartFab").addEventListener("click", async () => {
    drawerOpen();
    await refreshCart();
  });
  byId("drawerClose").addEventListener("click", drawerClose);
  byId("drawerScrim").addEventListener("click", drawerClose);

  byId("helpLink").addEventListener("click", (e) => {
    e.preventDefault();
    byId("checkoutHint").textContent =
      "Помощь: позже подключим чат с оператором через бота (кнопка откроет диалог).";
    drawerOpen();
  });

  byId("checkoutBtn").addEventListener("click", async () => {
    const cart = await refreshCart();
    const address = byId("address").value.trim();
    const deliveryTime = byId("deliveryTime").value.trim();

    if (!cart.items.length) {
      byId("checkoutHint").textContent = "Добавьте позиции в корзину.";
      return;
    }
    if (!address || !deliveryTime) {
      byId("checkoutHint").textContent = "Заполните адрес и время доставки.";
      return;
    }

    const customerTgId = getTgUserId() || getTgUserIdFromInput();
    if (!customerTgId) {
      byId("checkoutHint").textContent =
        "Не удалось определить Telegram ID. Введите его вручную (для отладки).";
      return;
    }

    const order = await apiPost("/orders", {
      cart_id: cartId,
      customer_tg_id: customerTgId,
      address,
      delivery_time: deliveryTime,
      customer_comment: "",
    });

    byId("checkoutHint").textContent =
      `Заказ #${order.id} отправлен на согласование. Ожидайте ответ в чате Telegram.`;
  });
}

main().catch((e) => {
  const hint = byId("checkoutHint");
  if (hint) hint.textContent = `Ошибка загрузки: ${String(e)}`;
});

