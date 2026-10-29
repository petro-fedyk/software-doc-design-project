import { api } from "./api.js";
import { auth } from "./auth.js";
import { localizeMarkup } from "../../web-shared/localize.js";
import { button, card, empty, escapeHtml as e, field, listOf, money, sectionHead, selectField, table } from "./ui.js";
const root = document.querySelector("#app");
let currentUser = null, message = "", messageType = "success", adminSections = [], renderGeneration = 0;
function flash(text, type = "success") { message = text; messageType = type; }
function page() { return location.hash.slice(1).split("?")[0] || (currentUser?.role === "ADMIN" ? "admin" : currentUser ? "staff" : "login"); }
function signedOut() { return `<section class="content narrow">${sectionHead("СЛУЖБОВИЙ ПОРТАЛ", "Вхід для працівників", "Доступ для персоналу аптек і адміністратора мережі.")}${card(`<form data-form="login">${field("Ім’я користувача", "username", "text", true)}${field("Пароль", "password", "password", true)}<button class="button primary full" type="submit">Увійти</button></form>`)}</section>`; }
function shell(content) { return `<header class="topbar"><a class="brand" href="#${currentUser?.role === "ADMIN" ? "admin" : "staff"}"><span class="brand-icon">+</span><span>goodwell<span class="brand-sub">УПРАВЛІННЯ МЕРЕЖЕЮ</span></span></a><nav class="main-nav">${currentUser ? `<a class="nav-link" href="#staff">Робота аптеки</a>${currentUser.role === "ADMIN" ? '<a class="nav-link" href="#admin">Адміністрування</a>' : ''}<button class="text-button" data-action="logout">Вийти</button>` : ''}</nav><span class="user-chip">${e(currentUser?.username || "Службовий вхід")}</span><button class="menu-toggle" data-action="menu" aria-label="Відкрити меню">☰</button></header><main>${message ? `<div class="notice ${messageType}" role="status">${e(message)}<button data-action="dismiss" aria-label="Закрити">×</button></div>` : ''}${content}</main><footer><span>Goodwell · службовий портал</span><span>Навчальний проєкт · оплати та доставка імітовані</span></footer>`; }
async function render() {
  const generation = ++renderGeneration;
  root.innerHTML = shell('<div class="page-loading">Завантаження…</div>');
  try {
    if (auth.token && !currentUser) currentUser = await auth.loadUser();
    const route = page();
    let content;
    if (!["login", "staff", "admin"].includes(route)) content = card('<h1>404 — Сторінку не знайдено</h1><a href="#login">До службового входу</a>');
    else if (!currentUser) content = signedOut();
    else if (route === "admin" && currentUser.role !== "ADMIN") content = card('<h1>Доступ заборонено</h1><p>Цей розділ доступний лише адміністратору.</p><a href="#staff">Робота аптеки</a>');
    else content = (route === "admin" || (route === "login" && currentUser.role === "ADMIN")) ? await adminPage() : await staffPage();
    if (generation === renderGeneration) root.innerHTML = localizeMarkup(shell(content));
  } catch(error) { if(generation === renderGeneration) root.innerHTML = shell(card(`<h1>Не вдалося завантажити сторінку</h1><p role="alert">${e(error.message)}</p>${button("Повторити", "retry")}`)); }
}
window.addEventListener("hashchange", render);
window.addEventListener("auth-expired", () => { auth.clear(); currentUser = null; flash("Сесію завершено. Увійдіть знову.", "error"); render(); });
const orderStatus = (status) => ({ PENDING_PAYMENT: "Очікує оплати", CONFIRMED: "Підтверджено", PROCESSING: "В обробці", READY_FOR_PICKUP: "Готове до самовивозу", AWAITING_SHIPMENT: "Очікує відправлення", SHIPPED: "Відправлено", COMPLETED: "Виконано", CANCELLED: "Скасовано" })[status] || status;
const adminLabels = { Users: "Користувачі", Pharmacies: "Аптеки", Products: "Товари", Categories: "Категорії", Manufacturers: "Виробники", Assignments: "Призначення персоналу", Promotions: "Акції", "Promotion products": "Товари акцій", "Loyalty tiers": "Рівні лояльності", "Delivery rules": "Правила доставки" };
const createLabels = { Users: "Створити користувача", Pharmacies: "Створити аптеку", Products: "Створити товар", Categories: "Створити категорію", Manufacturers: "Створити виробника", Assignments: "Створити призначення", Promotions: "Створити акцію", "Promotion products": "Прив’язати товар до акції", "Loyalty tiers": "Створити рівень лояльності", "Delivery rules": "Створити правило доставки" };
async function staffPage() {
  if (!currentUser || !["STAFF", "ADMIN"].includes(currentUser.role)) return signedOut();
  const ids = currentUser.role === "ADMIN" ? listOf(await api.listAll("/pharmacies/")).map((x) => x.id) : currentUser.pharmacy_ids;
  const id = Number(new URLSearchParams(location.hash.split("?")[1] || "").get("pharmacy")) || ids[0];
  const pharmacies = listOf(await api.listAll("/pharmacies/"));
  if (!id) return `<section class="content">${sectionHead("PHARMACY TEAM", "No assigned pharmacy", "Ask a network administrator to assign an active pharmacy to your account.")}</section>`;
  const [inventory, orders, stats] = await Promise.all([api.request(`/pharmacies/${id}/inventory/`), api.listAll("/orders/"), api.request(`/pharmacies/${id}/statistics/`)]);
  const branchOrders = listOf(orders).filter((x) => x.pharmacy_id === id);
  return `<section class="content">${sectionHead("РОБОТА АПТЕКИ", "Робоче місце аптеки", "API перевіряє призначення персоналу й дозволені операції для вибраної аптеки.")}<div class="staff-toolbar"><label class="field"><span>Призначена аптека</span><select data-action="branch-select">${pharmacies.filter((p) => ids.includes(p.id)).map((p) => `<option value="${p.id}" ${p.id === id ? "selected" : ""}>${e(p.name)} · ${e(p.city)}</option>`).join("")}</select></label><div class="stat-card"><span>Сума виконаних замовлень</span><b>${money(stats.completed_order_total)}</b></div><div class="stat-card"><span>Кількість станів замовлень</span><b>${stats.by_status?.length || 0}</b></div></div><div class="staff-grid"><div>${card(`<p class="eyebrow">ОБЛІК ЗАПАСІВ</p><h2>Залишки</h2>${table(["ТОВАР", "ДОСТУПНО / ВСЬОГО", "ЦІНА", "ЗМІНА"], listOf(inventory).map((x) => `<tr><td><b>${e(x.product__name)}</b><small>#${x.product_id} · ${x.is_listed ? "У продажу" : "Прихований"}</small></td><td>${x.available} / ${x.on_hand} · резерв ${x.reserved}</td><td>${money(x.unit_price)}</td><td><form class="stock-edit" data-form="stock" data-pharmacy="${id}" data-product="${x.product_id}" data-listed="${x.is_listed}"><input name="adjustment" type="number" placeholder="Зміна кількості ±"><input name="unit_price" type="number" min="0" step="0.01" placeholder="Ціна"><label class="check-row"><input name="is_listed" type="checkbox" ${x.is_listed ? "checked" : ""}>У продажу</label><button class="button secondary small" type="submit">Зберегти</button></form></td></tr>`))}`)}</div><div>${card(`<p class="eyebrow">ЗАМОВЛЕННЯ</p><h2>Замовлення аптеки</h2>${branchOrders.length ? branchOrders.map((o) => `<div class="staff-order"><div><b>#${e(o.order_number || o.id)}</b><small>${e(orderStatus(o.status))} · ${money(o.grand_total)}</small></div><div class="order-actions">${staffActions(o)}</div></div>`).join("") : empty("Замовлень немає", "Тут з’являтимуться замовлення аптеки.")}`)}${card(`<p class="eyebrow">ЖУРНАЛ ДІЙ</p><h2>Останні дії аптеки</h2><button class="button secondary" data-action="audit" data-id="${id}">Завантажити журнал</button><div id="audit-${id}"></div>`)}</div></div></section>`;
}

function staffActions(o) {
  const next = o.status === "CONFIRMED" ? ["PROCESSING"] : o.status === "PROCESSING" ? (o.fulfillment_method === "PICKUP" ? ["READY_FOR_PICKUP"] : ["AWAITING_SHIPMENT"]) : o.status === "READY_FOR_PICKUP" || o.status === "SHIPPED" ? ["COMPLETED"] : [];
  const pharmacistActions = currentUser?.role === "STAFF" && currentUser?.pharmacist
    ? `${button("Approve prescription", "verify-prescription", "small", `data-id="${o.id}" data-approved="true"`)}${button("Reject prescription", "verify-prescription", "small danger-text", `data-id="${o.id}" data-approved="false"`)}`
    : "";
  return `${next.map((status) => button(orderStatus(status), "transition", "small", `data-id="${o.id}" data-status="${status}"`)).join("")}${o.status === "AWAITING_SHIPMENT" ? button("Передати на доставку", "ship", "small", `data-id="${o.id}"`) : ""}${pharmacistActions}${o.status === "CANCELLED" ? button("Оформити повернення", "refund", "small", `data-id="${o.id}"`) : ""}`;
}

async function adminPage() {
  if (!currentUser || currentUser.role !== "ADMIN") return signedOut();
  const sections = [
    ["Users", "/admin/users/", [["username", "Username"], ["email", "Email"], ["role", "Role"], ["is_active", "Active"]]],
    ["Pharmacies", "/pharmacies/", [["code", "Code"], ["name", "Name"], ["city", "City"], ["is_active", "Active"]]],
    ["Products", "/products/", [["sku", "SKU"], ["name", "Name"], ["description", "Description"], ["category", "Category"], ["manufacturer", "Manufacturer"], ["prescription_required", "Prescription required"], ["storage_min_c", "Storage minimum °C"], ["storage_max_c", "Storage maximum °C"], ["is_active", "Active"]]],
    ["Categories", "/categories/", [["name", "Name"]]], ["Manufacturers", "/manufacturers/", [["name", "Name"]]],
    ["Assignments", "/admin/assignments/", [["user", "User ID"], ["pharmacy", "Pharmacy ID"], ["is_active", "Active"]]],
    ["Promotions", "/admin/promotions/", [["code", "Code"], ["description", "Description"], ["discount_rate", "Discount rate"], ["starts_at", "Starts at"], ["ends_at", "Ends at"], ["is_active", "Active"]]],
    ["Promotion products", "/admin/promotion-products/", [["promotion", "Promotion ID"], ["product", "Product ID"]]],
    ["Loyalty tiers", "/admin/loyalty-tiers/", [["code", "Code"], ["bonus_rate", "Bonus rate"], ["discount_rate", "Discount rate"]]],
    ["Delivery rules", "/admin/delivery-rules/", [["method", "Method"], ["enabled", "Enabled"], ["requires_cold_chain", "Cold chain"], ["cold_chain_supported", "Supported"]]],
  ];
  adminSections = sections;
  const data = await api.request("/admin/statistics/");
  return `<section class="content">${sectionHead("NETWORK ADMINISTRATION", "Network overview", "All privileged changes are sent to the API and checked against your ADMIN role.")}<div class="stats-row">${card(`<p class="eyebrow">COMPLETED ORDER TOTAL</p><b class="stat-number">${money(data.completed_order_total)}</b>`)}${card(`<p class="eyebrow">ORDER STATUSES</p><b class="stat-number">${data.by_status?.length || 0}</b>`)}${card(`<p class="eyebrow">ACCESS</p><b class="stat-number">Administrator</b>`)}</div><div class="admin-tabs">${sections.map(([name, path], i) => `<button class="admin-tab ${i === 0 ? "active" : ""}" data-action="admin-section" data-path="${path}" data-name="${name}">${e(adminLabels[name] || name)}</button>`).join("")}<button class="admin-tab" data-action="admin-audit">Журнал аудиту</button></div><div id="admin-content" class="admin-content">${await adminTable(sections[0])}</div><div id="admin-audit-content" class="admin-content"></div></section>`;
}

async function editAdminRow(target) {
  const path = target.dataset.path;
  const record = await api.request(`${path}${target.dataset.id}/`);
  const columns = JSON.parse(target.dataset.columns);
  const fields = columns.map(([key, label]) => {
    const value = record[key];
    if (typeof value === "boolean") return `<label class="check-row"><input type="checkbox" name="${key}" ${value ? "checked" : ""}>${e(label)}</label>`;
    const type = key.endsWith("_at") ? "datetime-local" : typeof value === "number" ? "number" : "text";
    const display = type === "datetime-local" && value ? new Date(value).toISOString().slice(0, 16) : value ?? "";
    return field(e(adminFieldLabel(label)), key, type, false, display);
  }).join("");
  document.querySelector("#admin-edit-dialog")?.remove();
  root.insertAdjacentHTML("beforeend", `<dialog id="admin-edit-dialog"><form data-form="admin-edit" data-path="${path}" data-id="${target.dataset.id}"><h2>Редагування запису №${target.dataset.id}</h2>${fields}<div class="button-row"><button type="button" class="button secondary" data-action="close-dialog">Скасувати</button><button class="button primary" type="submit">Зберегти зміни</button></div></form></dialog>`);
  const dialog = document.querySelector("#admin-edit-dialog");
  dialog.showModal();
}

async function adminTable(section, pageNumber = 1) {
  const [name, path, columns] = section;
  const data = await api.request(`${path}?page=${pageNumber}`);
  const rows = listOf(data);
  const output = rows.map((r) => `<tr><td>${r.id}</td>${columns.map(([key]) => `<td>${e(String(r[key] ?? "—"))}</td>`).join("")}<td><button class="text-button" data-action="edit-row" data-path="${path}" data-id="${r.id}" data-columns="${e(JSON.stringify(columns))}">Edit</button></td></tr>`);
  const newForms = {
    Users: [["username", "Username", "text"], ["email", "Email", "email"], ["role", "Role: CUSTOMER, STAFF, ADMIN", "text"], ["password", "Temporary password (12+ chars)", "password"]],
    Pharmacies: [["code", "Code", "text"], ["name", "Name", "text"], ["address", "Address", "text"], ["city", "City", "text"], ["phone", "Phone", "tel"]],
    Products: [["sku", "SKU", "text"], ["name", "Name", "text"], ["description", "Description", "text"], ["category", "Category ID", "number"], ["manufacturer", "Manufacturer ID", "number"]],
    Categories: [["name", "Name", "text"]], Manufacturers: [["name", "Name", "text"]],
    Assignments: [["user", "Staff user ID", "number"], ["pharmacy", "Pharmacy ID", "number"]],
    "Promotions": [["code", "Code", "text"], ["description", "Description", "text"], ["discount_rate", "Discount rate 0–1", "number"], ["starts_at", "Starts at (ISO date/time)", "datetime-local"], ["ends_at", "Ends at (ISO date/time)", "datetime-local"]],
    "Loyalty tiers": [["code", "Code", "text"], ["bonus_rate", "Bonus rate 0–1", "number"], ["discount_rate", "Discount rate 0–1", "number"]],
    "Promotion products": [["promotion", "Promotion ID", "number"], ["product", "Product ID", "number"]],
    "Delivery rules": [["method", "Method: PICKUP, COURIER, POSTAL", "text"], ["requires_cold_chain", "Requires cold chain", "checkbox"], ["cold_chain_supported", "Cold chain supported", "checkbox"], ["enabled", "Enabled", "checkbox"], ["max_storage_min_c", "Maximum storage minimum °C", "number"], ["min_storage_max_c", "Minimum storage maximum °C", "number"]],
  };
  const fields = newForms[name] || [];
  const label = adminLabels[name] || name;
  return `<div class="table-toolbar"><div><p class="eyebrow">${e(label.toLocaleUpperCase("uk-UA"))}</p><h2>${data.count ?? rows.length} записів · сторінка ${pageNumber}</h2></div><button class="button secondary" data-action="toggle-create">＋ Новий запис</button></div>${rows.length ? table(["ID", ...columns.map((x) => e(adminFieldLabel(x[1]).toLocaleUpperCase("uk-UA"))), ""], output) : empty("Записів немає", "Створіть перший запис за допомогою форми.")}<div class="catalog-foot"><button class="text-button" data-action="admin-page" data-path="${path}" data-name="${e(name)}" data-page="${pageNumber - 1}" ${pageNumber <= 1 ? "disabled" : ""}>← Попередня</button><span>Сторінка ${pageNumber} · ${rows.length} у списку</span><button class="text-button" data-action="admin-page" data-path="${path}" data-name="${e(name)}" data-page="${pageNumber + 1}" ${data.next ? "" : "disabled"}>Наступна →</button></div><form class="admin-create hidden" data-form="admin-create" data-path="${path}">${fields.map(([key, label, type]) => key === "role" ? selectField("Роль", "role", [["STAFF", "Працівник"], ["ADMIN", "Адміністратор"], ["CUSTOMER", "Покупець"]], true) : type === "checkbox" ? `<label class="check-row"><input type="checkbox" name="${key}">${e(adminFieldLabel(label))}</label>` : field(e(adminFieldLabel(label)), key, type, !["description", "phone", "max_storage_min_c", "min_storage_max_c"].includes(key))).join("")}<button class="button primary" type="submit">${createLabels[name] || "Створити запис"}</button></form>`;
}

function adminFieldLabel(label) {
  return ({ Username: "Ім’я користувача", Email: "Електронна пошта", Role: "Роль", Active: "Активний", Code: "Код", Name: "Назва", City: "Місто", Address: "Адреса", Phone: "Телефон", Description: "Опис", Category: "Категорія", Manufacturer: "Виробник", "Prescription required": "Потрібен рецепт", "Storage minimum °C": "Мінімальна температура зберігання, °C", "Storage maximum °C": "Максимальна температура зберігання, °C", "User ID": "ID користувача", "Pharmacy ID": "ID аптеки", "Promotion ID": "ID акції", "Product ID": "ID товару", "Discount rate": "Розмір знижки", "Discount rate 0–1": "Розмір знижки 0–1", "Bonus rate": "Бонусна ставка", "Bonus rate 0–1": "Бонусна ставка 0–1", "Starts at": "Початок дії", "Ends at": "Кінець дії", Method: "Спосіб", Enabled: "Увімкнено", "Requires cold chain": "Потрібен холодовий ланцюг", "Cold chain supported": "Холодовий ланцюг доступний", "Staff user ID": "ID працівника", "Method: PICKUP, COURIER, POSTAL": "Спосіб: PICKUP, COURIER, POSTAL" })[label] || label;
}


root.addEventListener("click", async event => {
 const target = event.target.closest("[data-action]"); if(!target) return;
 const action = target.dataset.action;
 if(target.disabled) return;
 target.disabled = true;
 try {
  if(action === "logout") { auth.clear(); currentUser = null; message = ""; location.hash = "login"; render(); }
  if(action === "dismiss") { message = ""; render(); }
  if(action === "retry") render();
  if(action === "menu") document.querySelector(".main-nav")?.classList.toggle("open");
    if (action === "fulfillment") { const data = await api.request(`/orders/${target.dataset.id}/fulfillment/`); const box = document.querySelector(`#fulfillment-${target.dataset.id}`); box.innerHTML = `<pre>${e(JSON.stringify(data, null, 2))}</pre>`; }
    if (action === "transition") { await api.request(`/orders/${target.dataset.id}/transition/`, { method: "POST", body: { status: target.dataset.status } }); flash("Order status updated by the API."); render(); }
    if (action === "ship") { await api.request(`/orders/${target.dataset.id}/ship/`, { method: "POST", body: {} }); flash("Shipment request queued."); render(); }
    if (action === "verify-prescription") { const approved = target.dataset.approved === "true"; await api.request(`/orders/${target.dataset.id}/verify-prescription/`, { method: "POST", body: { approved } }); flash(approved ? "Рецепт перевірено та схвалено." : "Рецепт відхилено."); render(); }
    if (action === "refund") { const amount = prompt("Сума повернення (UAH)"); if (amount && Number(amount) > 0) { const reason = prompt("Причина повернення"); if (reason) { await api.request(`/orders/${target.dataset.id}/refund/`, { method: "POST", body: { amount, reason, idempotency_key: crypto.randomUUID() } }); flash("Запит на імітоване повернення прийнято."); render(); } } }
    if (action === "audit") { const data = await api.request(`/pharmacies/${target.dataset.id}/audit/`); document.querySelector(`#audit-${target.dataset.id}`).innerHTML = `<pre>${e(JSON.stringify(data, null, 2))}</pre>`; }
    if (action === "admin-audit") { const data = await api.request("/admin/audit/"); document.querySelector("#admin-audit-content").innerHTML = table(["ID", "ACTOR", "ACTION", "TARGET", "WHEN"], listOf(data).map((x) => `<tr><td>${x.id}</td><td>${e(x.actor_id ?? "—")}</td><td>${e(x.action)}</td><td>${e(x.target_type)} ${e(x.target_id ?? "")}</td><td>${e(new Date(x.occurred_at).toLocaleString("uk-UA"))}</td></tr>`)); }
    if (action === "toggle-create") document.querySelector(".admin-create")?.classList.toggle("hidden");
    if (action === "close-dialog") target.closest("dialog")?.close();
    if (action === "admin-section") { const name = target.dataset.name; const section = adminSections.find((x) => x[0] === name); if (section) document.querySelector("#admin-content").innerHTML = await adminTable(section); document.querySelectorAll(".admin-tab").forEach((b) => b.classList.toggle("active", b === target)); }
    if (action === "admin-page") { const section = adminSections.find((x) => x[1] === target.dataset.path); if (section && Number(target.dataset.page) > 0) document.querySelector("#admin-content").innerHTML = await adminTable(section, Number(target.dataset.page)); }
    if (action === "edit-row") await editAdminRow(target);
 } catch(error) { flash(error.message,"error"); render(); }
 finally { target.disabled = false; }
});
root.addEventListener("change", event => { if(event.target.matches('[data-action="branch-select"]')) location.hash = `staff?pharmacy=${event.target.value}`; });
root.addEventListener("submit", async event => {
 const form = event.target.closest('form[data-form]'); if(!form) return; event.preventDefault();
 const submitButton = form.querySelector('[type="submit"]'); if(submitButton) submitButton.disabled = true;
 const kind = form.dataset.form, raw = Object.fromEntries(new FormData(form).entries());
 try {
  if(kind === "login") { currentUser = await auth.signIn(raw.username,raw.password); flash("Вхід успішний."); location.hash = currentUser.role === "ADMIN" ? "admin" : "staff"; render(); }
    if (kind === "stock") { const body = {}; if (raw.adjustment) body.adjustment = Number(raw.adjustment); if (raw.unit_price) body.unit_price = raw.unit_price; const listed = form.elements.is_listed.checked; if (String(listed) !== form.dataset.listed) body.is_listed = listed; if (!Object.keys(body).length) throw new Error("Вкажіть зміну залишку, ціни або доступності товару."); await api.request(`/pharmacies/${form.dataset.pharmacy}/inventory/${form.dataset.product}/`, { method: "PATCH", body }); flash("Зміни залишку підтверджено сервером."); render(); }
    if (kind === "admin-create") { const body = Object.fromEntries(Object.entries(raw).filter(([key, v]) => form.elements[key]?.type === "checkbox" || v !== "")); for (const box of form.querySelectorAll('input[type="checkbox"]')) body[box.name] = box.checked; for (const key of ["category", "manufacturer", "user", "pharmacy", "promotion", "product"]) if (body[key]) body[key] = Number(body[key]); for (const key of ["discount_rate", "bonus_rate", "storage_min_c", "storage_max_c", "max_storage_min_c", "min_storage_max_c"]) if (key in body && body[key] !== "") body[key] = Number(body[key]); if (body.starts_at) body.starts_at = new Date(body.starts_at).toISOString(); if (body.ends_at) body.ends_at = new Date(body.ends_at).toISOString(); const path = form.dataset.path; if (["/admin/users/", "/pharmacies/", "/admin/assignments/", "/admin/promotions/"].includes(path)) body.is_active = true; if (path === "/products/") body.is_active = true; await api.request(path, { method: "POST", body }); flash("Запис створено на сервері."); render(); }
    if (kind === "admin-edit") { const body = {}; for (const input of form.querySelectorAll("input")) { const key = input.name; if (!key) continue; if (input.type === "checkbox") body[key] = input.checked; else if (input.value === "") body[key] = ["storage_min_c", "storage_max_c"].includes(key) ? null : ""; else if (input.type === "number") body[key] = Number(input.value); else if (key.endsWith("_at")) body[key] = new Date(input.value).toISOString(); else body[key] = input.value; } await api.request(`${form.dataset.path}${form.dataset.id}/`, { method: "PATCH", body }); form.closest("dialog")?.close(); flash("Зміни збережено на сервері."); render(); }
 } catch(error) { flash(error.message,"error"); render(); }
 finally { if(submitButton) submitButton.disabled = false; }
});
render();
