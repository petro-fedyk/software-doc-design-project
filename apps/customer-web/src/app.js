import { api } from "./api.js";
import { auth } from "./auth.js";
import { demoPaymentRequestPayload, isFictionalDemoCard } from "./payment-demo.js";
import { button, card, empty, escapeHtml as e, field, listOf, money, sectionHead, selectField, table } from "./ui.js";

const root = document.querySelector("#app");
let currentUser = auth.user;
let busy = false;
let message = "";
let messageType = "success";
let catalogFilters = { search: "", category: "", manufacturer: "", pharmacy: "" };
let catalogPageNumber = 1;
let pendingOrder = null;
let renderGeneration = 0;
let headerBonusBalance = null;
let selectedPharmacyId = localStorage.getItem("pharmacy.selectedBranch") || "";
let branchAssetsPromise;
let productAssetsPromise;
let categoryCatalogPromise;
let addToCartQueue = Promise.resolve();
let addToCartNavigationTimer;
const href = (route) => `#${route}`;
const CATALOG_CATEGORY_OPTIONS = [
  ["Pain management", "Знеболювальні препарати"],
  ["Digestive health", "Засоби для травлення"],
  ["Respiratory care", "Засоби від застуди та для дихання"],
  ["Pediatric care", "Дитячі препарати"],
  ["Anti-infectives", "Протиінфекційні препарати"],
];

import { localizeMarkup } from "../../web-shared/localize.js";
const orderStatus = (status) => ({ PENDING_CONFIRMATION: "Очікує підтвердження аптеки", PENDING_PAYMENT: "Очікує оплати", PENDING: "Обробляється", UNKNOWN: "Очікує результату симуляції", CONFIRMED: "Підтверджено аптекою", PROCESSING: "В обробці", READY_FOR_PICKUP: "Готове до самовивозу", AWAITING_SHIPMENT: "Очікує відправлення", SHIPPED: "Відправлено", COMPLETED: "Виконано", CANCELLED: "Скасовано", SUCCEEDED: "Оплачено (симуляція)", FAILED: "Відхилено (симуляція)" })[status] || status;
const cancellationReasonLabel = (code) => ({ OUT_OF_STOCK: "Товар закінчився", PRICE_CHANGED: "Змінилася ціна", PRESCRIPTION_ISSUE: "Проблема з рецептом", DELIVERY_UNAVAILABLE: "Немає доставки до адреси", OTHER: "Інша причина", CUSTOMER_REQUEST: "Скасовано покупцем" })[code] || code;
const paymentMethod = (method) => ({ CARD: "Картка ", BANK_TRANSFER: "Банківський переказ ", CASH_ON_DELIVERY: "Оплата при отриманні ", ONLINE_GATEWAY: "Онлайн-шлюз " })[method] || method;

window.addEventListener("hashchange", () => render({ scrollToTop: true }));
window.addEventListener("auth-expired", () => { auth.clear(); currentUser = null; flash("Сесію завершено. Увійдіть знову.", "error"); render(); });
window.addEventListener("DOMContentLoaded", () => {});

function flash(text, type = "success") { message = text; messageType = type; }
function page() { return (location.hash.replace(/^#/, "").split("?")[0]) || "home"; }
function navLink(name, route, active) { return `<a class="nav-link ${active ? "active" : ""}" href="${href(route)}">${name}</a>`; }
async function branchAssets() {
  if (!branchAssetsPromise) branchAssetsPromise = fetch("/data/anc_branches.json").then((r) => r.ok ? r.json() : []).catch(() => []);
  return new Map((await branchAssetsPromise).map((branch) => [branch.code, branch]));
}
async function productAssets() {
  if (!productAssetsPromise) productAssetsPromise = fetch("/data/product_images.json").then((r) => r.ok ? r.json() : {}).catch(() => ({}));
  return productAssetsPromise;
}
async function categoryCatalog() {
  if (!categoryCatalogPromise) {
    categoryCatalogPromise = (async () => {
      const categories = [];
      for (let page = 1; ; page += 1) {
        const data = await api.request(`/categories/${page > 1 ? `?page=${page}` : ""}`, { auth: false });
        categories.push(...listOf(data));
        if (!data?.next) break;
      }
      return categories;
    })().catch((error) => {
      categoryCatalogPromise = null;
      throw error;
    });
  }
  return categoryCatalogPromise;
}
function productImage(product, assets) {
  const source = assets[product.sku] || {};
  return { url: product.image_url || source.image_url || "", source: product.image_source_url || source.source_url || "" };
}
async function choosePharmacy(pharmacyId) {
  const next = String(pharmacyId || "");
  if (!next || next === String(selectedPharmacyId)) return;
  selectedPharmacyId = next;
  localStorage.setItem("pharmacy.selectedBranch", next);
}
function cartBranchStorageKey() { return `pharmacy.cartBranches.${currentUser?.username || "guest"}`; }
function readCartBranches() {
  try {
    const value = JSON.parse(localStorage.getItem(cartBranchStorageKey()) || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch { return {}; }
}
function writeCartBranches(value) { localStorage.setItem(cartBranchStorageKey(), JSON.stringify(value)); }
async function captureGuestCart() {
  try {
    const response = await api.request("/guest-cart/", { auth: false });
    const rawItems = response.items || {};
    const items = Array.isArray(rawItems)
      ? rawItems.map((item) => [Number(item.product_id), Number(item.quantity)])
      : Object.entries(rawItems).map(([id, quantity]) => [Number(id), Number(quantity)]);
    let branchMap = {};
    try { branchMap = JSON.parse(localStorage.getItem("pharmacy.cartBranches.guest") || "{}"); } catch { /* Use the selected pharmacy if there is no guest mapping. */ }
    return { items: items.filter(([id, quantity]) => Number.isInteger(id) && id > 0 && Number.isInteger(quantity) && quantity > 0), branchMap };
  } catch {
    return null;
  }
}
async function mergeGuestCart(snapshot) {
  if (currentUser?.role !== "CUSTOMER") return 0;
  const pendingKey = `pharmacy.pendingGuestCartMerge.${currentUser.username}`;
  let pending;
  try { pending = JSON.parse(localStorage.getItem(pendingKey) || "null"); } catch { pending = null; }
  if (!pending) {
    if (!snapshot?.items?.length) return 0;
    const cart = await api.request("/cart/");
    const existingItems = Array.isArray(cart.items) ? cart.items : Object.entries(cart.items || {}).map(([id, quantity]) => ({ product_id: Number(id), quantity }));
    const existing = new Map(existingItems.map((item) => [Number(item.product_id), Number(item.quantity)]));
    const plan = snapshot.items.map(([productId, quantity]) => [productId, Math.min(10000, (existing.get(productId) || 0) + quantity)]);
    pending = { plan, guestIds: snapshot.items.map(([productId]) => productId), accountIds: [...existing.keys()], branchMap: snapshot.branchMap || {} };
    localStorage.setItem(pendingKey, JSON.stringify(pending));
  }
  for (const [productId, quantity] of pending.plan) {
    await api.request("/cart/", { method: "PUT", body: { product_id: productId, quantity, allow_unavailable: true } });
  }
  await api.request("/guest-cart/", { method: "DELETE", auth: false });
  const accountBranches = readCartBranches();
  for (const productId of pending.guestIds) {
    if (!pending.accountIds.includes(productId) && pending.branchMap[String(productId)]) {
      accountBranches[productId] = String(pending.branchMap[String(productId)]);
    }
  }
  writeCartBranches(accountBranches);
  localStorage.removeItem(pendingKey);
  return pending.plan.length;
}
function addCartControl(productId, productName, style = "button primary add-to-cart", pharmacyId = "") {
  if (currentUser && currentUser.role !== "CUSTOMER") return `<span class="muted" aria-label="Покупки доступні клієнтам">Кошик для клієнтів</span>`;
  return `<button class="${style}" data-action="add" data-id="${productId}" data-pharmacy="${e(pharmacyId)}" aria-label="Додати до кошика: ${e(productName)}">До кошика <span aria-hidden="true">→</span></button>`;
}
function shell(content) {
  const route = page().split(":")[0];
  const user = currentUser;

  return `<header class="topbar"><a class="brand" href="#home"><span class="brand-icon">+</span><span>goodwell<span class="brand-sub">МЕРЕЖА АПТЕК</span></span></a><nav class="main-nav">${navLink("Shop", "home", ["home", "product"].includes(route))}${navLink("Locations", "pharmacies", route === "pharmacies")}${user?.role === "CUSTOMER" ? navLink("My account", "account", route === "account" || route === "orders") : ""}${user ? '<button class="text-button mobile-logout" data-action="logout">Вийти</button>' : ""}</nav><div class="nav-actions">${user ? `<span class="user-chip">${e(user.username)} <small>${e(user.role)}</small>${user.role === "CUSTOMER" && headerBonusBalance !== null ? `<small class="user-bonus">${e(headerBonusBalance)} бонусів</small>` : ""}</span><button class="text-button" data-action="logout">Sign out</button>` : navLink("Sign in", "login", route === "login")}${navLink("Bag", "cart", route === "cart")}<span class="bag-dot">+</span></div><button class="menu-toggle" data-action="menu" aria-label="Відкрити меню">☰</button></header><main id="home">${message ? `<div class="notice ${messageType}" role="status">${e(message)}<button data-action="dismiss" aria-label="Закрити повідомлення">×</button></div>` : ""}${busy ? `<div class="loading-bar"><span></span></div>` : ""}${content}</main><footer><div class="footer-brand">goodwell<span>турбота щодня</span></div><div class="footer-links"><a href="#pharmacies">Наші аптеки</a><a href="#account">Підтримка клієнтів</a><span>Резервування онлайн · актуальність підтверджує аптека</span></div></footer>`;
}

async function render({ scrollToTop = false } = {}) {
  const generation = ++renderGeneration;
  const route = page();
  busy = true;
  root.innerHTML = shell(`<div class="page-loading">Loading…</div>`);
  try {
    if (auth.token && !currentUser) currentUser = await auth.loadUser();
    if (currentUser?.role === "CUSTOMER" && localStorage.getItem(`pharmacy.pendingGuestCartMerge.${currentUser.username}`)) {
      try {
        const count = await mergeGuestCart(await captureGuestCart());
        flash(`Перенесення гостьового кошика завершено: ${count} позицій.`);
      } catch (error) {
        flash(`Гостьовий кошик збережений і буде повторно перенесений після виправлення помилки: ${error.message}`, "error");
      }
    }
    let content;
    if (route === "home") content = await catalogPage({ showHero: true });
    else if (route === "catalog") content = await catalogPage({ showHero: false });
    else if (route.startsWith("product:")) content = await productPage(route.split(":")[1]);
    else if (route === "pharmacies") content = await pharmaciesPage();
    else if (route.startsWith("pharmacy:")) content = await pharmacyPage(route.split(":")[1]);
    else if (route === "cart") content = await cartPage();
    else if (route === "login" || route === "register") content = authPage(route);
    else if (route === "account") content = await accountPage();
    else if (route === "orders") content = await ordersPage();
    else if (route.startsWith("pay:")) content = await demoPaymentPage(route.split(":")[1]);
    else content = notFoundPage();
    if (generation !== renderGeneration) return;
    if (currentUser?.role === "CUSTOMER") {
      try {
        const loyalty = await api.request("/loyalty/");
        headerBonusBalance = Number(loyalty.account?.balance ?? 0);
      } catch { headerBonusBalance = null; }
    } else {
      headerBonusBalance = null;
    }
    if (generation !== renderGeneration) return;
    busy = false;
    root.innerHTML = localizeMarkup(shell(content));
    if (scrollToTop) window.scrollTo({ top: 0, behavior: "instant" });
  } catch (error) {
    if (generation !== renderGeneration) return;
    busy = false;
    root.innerHTML = localizeMarkup(shell(`<section class="content narrow">${sectionHead("WE HIT A SNAG", "This page could not load")}${card(`<div class="error-panel"><strong>${e(error.message)}</strong><p>Try again once the API is available.</p>${button("Retry", "retry", "secondary")}</div>`)}</section>`));
    if (scrollToTop) window.scrollTo({ top: 0, behavior: "instant" });
  }
}

function notFoundPage() {
  return `<section class="content narrow">${sectionHead("404", "Сторінку не знайдено", "Перевірте адресу або поверніться до каталогу.")}${card(`<a class="button primary" href="#home">До каталогу</a>`)}</section>`;
}

async function catalogPage({ showHero = false } = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(catalogFilters)) {
    if (key === "pharmacy" || !value) continue;
    if (key === "category" && value === "prescription") query.set("prescription_required", "true");
    else query.set(key, value);
  }
  if (catalogPageNumber > 1) query.set("page", String(catalogPageNumber));
  const [allCategories, manufacturerData, pharmacyData] = await Promise.all([
    categoryCatalog(), api.request("/manufacturers/", { auth: false }), api.listAll("/pharmacies/", { auth: false }),
  ]);
  const categories = CATALOG_CATEGORY_OPTIONS.map(([name, label]) => ({
    ...allCategories.find((category) => category.name === name), label,
  })).filter((category) => category.id !== undefined), manufacturers = listOf(manufacturerData), pharmacies = listOf(pharmacyData).filter((x) => x.is_active !== false);
  const images = await productAssets();
  if (catalogFilters.pharmacy && !pharmacies.some((x) => String(x.id) === String(catalogFilters.pharmacy))) catalogFilters.pharmacy = "";
  const completeProductQuery = new URLSearchParams(query);
  completeProductQuery.delete("page");
  const [productData, inventoryData] = await Promise.all([
    catalogFilters.pharmacy
      ? api.listAll(`/products/${completeProductQuery.size ? `?${completeProductQuery}` : ""}`, { auth: currentUser?.role === "ADMIN" })
      : api.listAll(`/products/${completeProductQuery.size ? `?${completeProductQuery}` : ""}`, { auth: currentUser?.role === "ADMIN" }),
    catalogFilters.pharmacy
      ? api.request(`/pharmacies/${encodeURIComponent(catalogFilters.pharmacy)}/inventory/`, { auth: false })
      : Promise.resolve([]),
  ]);
  const listedProductIds = new Set(listOf(inventoryData).map((row) => Number(row.product_id)));
  const allProducts = listOf(productData);
  const products = catalogFilters.pharmacy ? allProducts.filter((product) => listedProductIds.has(Number(product.id))) : allProducts;
  const displayedProductData = { ...productData, count: catalogFilters.pharmacy ? products.length : (productData.count ?? products.length) };
  const inventoryByProduct = new Map(listOf(inventoryData).map((x) => [Number(x.product_id), x]));
  const byId = (items, id) => items.find((item) => item.id === id)?.name || "—";
  const hero = showHero ? `<section class="hero"><div class="hero-copy"><p class="eyebrow">ТУРБОТА ПОРУЧ</p><h1>Турбота щодня,<br><em>для вашого здоров’я.</em></h1><p>Необхідні товари та турбота аптеки — поруч, коли вони потрібні.</p><a class="button primary" href="#catalog">Переглянути товари <span>↗</span></a><div class="hero-proof"><span>●</span> Мережа аптек <b>·</b> Зручне замовлення</div></div><div class="hero-art" aria-label="Ілюстрація рослини"><div class="sun"></div><div class="leaf leaf-one"></div><div class="leaf leaf-two"></div><div class="plant-stem"></div><div class="jar"><span>g</span></div><div class="art-label">турбота<br>щодня</div></div></section>` : "";
  return `${hero}<section class="content" id="catalog"><div class="section-head"><div><p class="eyebrow">КАТАЛОГ АПТЕКИ</p><h2>Оберіть потрібне</h2><p class="muted">Торгові назви препаратів справжні. Ціни й залишки нижче — навчальна симуляція.</p></div><div class="result-note">${displayedProductData.count} товарів ${catalogFilters.pharmacy ? "у вибраній аптеці" : "в каталозі"}</div></div><form class="filterbar" data-form="filters"><label class="search-field"><span>⌕</span><input name="search" value="${e(catalogFilters.search)}" placeholder="Пошук за назвою або SKU" aria-label="Пошук"></label><select name="category"><option value="">Усі категорії</option><option value="prescription" ${catalogFilters.category === "prescription" ? "selected" : ""}>Рецептурні препарати · самовивіз</option>${categories.map((x) => `<option value="${x.id}" ${String(catalogFilters.category) === String(x.id) ? "selected" : ""}>${e(x.label)}</option>`).join("")}</select><select name="manufacturer"><option value="">Усі виробники</option>${manufacturers.map((x) => `<option value="${x.id}" ${String(catalogFilters.manufacturer) === String(x.id) ? "selected" : ""}>${e(x.name)}</option>`).join("")}</select><select name="pharmacy" aria-label="Аптека"><option value="">Усі аптеки</option>${pharmacies.map((x) => `<option value="${x.id}" ${String(catalogFilters.pharmacy) === String(x.id) ? "selected" : ""}>${e(x.name)} · ${e(x.city)} · ${e(x.address || "")}</option>`).join("")}</select><button class="button secondary" type="submit">Застосувати фільтри</button><button class="button secondary" type="button" data-action="reset-filters">Скинути фільтри</button></form><div class="product-grid">${products.length ? products.map((p, i) => { const stock = inventoryByProduct.get(Number(p.id)); const image = productImage(p, images); const available = Number(stock?.available || 0); return `<article class="product-card" data-product-card data-route="product:${p.id}" role="link" tabindex="0" aria-label="Переглянути ${e(p.name)}"><a class="product-image tone-${i % 4}" href="#product:${p.id}"><span class="product-number">${String(i + 1).padStart(2, "0")}</span>${image.url ? `<img class="product-photo" src="${e(image.url)}" alt="${e(p.name)}" loading="lazy" onerror="this.hidden=true">` : `<span class="bottle"></span>`}<span class="product-tag ${p.prescription_required ? "prescription-label" : "otc-label"}">${p.prescription_required ? "ЗА РЕЦЕПТОМ" : "БЕЗ РЕЦЕПТА"}</span></a><div class="product-info"><p class="product-meta">${e(byId(allCategories, p.category))} · ${e(byId(manufacturers, p.manufacturer))}</p><h3><a href="#product:${p.id}">${e(p.name)}</a></h3><p class="product-description">${e(p.description || "Фармацевтичний препарат або товар для здоров’я.")}</p><div class="product-foot"><span class="catalog-stock">${stock ? `${money(stock.unit_price)} · ${available > 0 ? `у наявності: ${available}` : "немає в наявності"}` : (catalogFilters.pharmacy ? "немає в наявності" : "Оберіть аптеку для уточнення ціни")}</span>${!catalogFilters.pharmacy ? `<a class="button primary" href="#product:${p.id}">Знайти в аптеках</a>` : stock && available > 0 ? addCartControl(p.id, p.name, "button primary add-to-cart", catalogFilters.pharmacy) : `<span class="muted" aria-label="Товар недоступний">Немає в наявності</span>`}</div></div></article>`; }).join("") : empty("Товарів не знайдено", "Змініть пошук або приберіть фільтр.")}</div><div class="catalog-foot"><span>Показано ${products.length} із ${displayedProductData.count}</span></div></section><section class="service-strip"><span>✳ Ціни й залишки за вибраною аптекою</span><span>⌂ Самовивіз та доставка</span><span>♡ Одне замовлення — одна аптека</span></section>`;
}

async function productPage(id) {
  const p = await api.request(`/products/${encodeURIComponent(id)}/`, { auth: false });
  const [availableResult, categories, manufacturers, pharmacyData] = await Promise.allSettled([api.request(`/products/${p.id}/availability/`, { auth: false }), api.request("/categories/", { auth: false }), api.request("/manufacturers/", { auth: false }), api.listAll("/pharmacies/", { auth: false })]);
  if (categories.status === "rejected" || manufacturers.status === "rejected" || pharmacyData.status === "rejected") throw (categories.reason || manufacturers.reason || pharmacyData.reason);
  const image = productImage(p, await productAssets());
  const availabilityError = availableResult.status === "rejected" ? availableResult.reason : null;
  const pharmacies = listOf(pharmacyData.value);
  const pharmacyById = new Map(pharmacies.map((x) => [Number(x.id), x]));
  const available = availableResult.status === "fulfilled" ? listOf(availableResult.value).filter((x) => Number(x.available) > 0) : [];
  const chosen = available.find((x) => String(x.pharmacy_id) === String(selectedPharmacyId)) || available[0];
  const branch = chosen && pharmacyById.get(Number(chosen.pharmacy_id));
  const stockCard = chosen ? `<div class="product-stock-card"><div><span class="eyebrow">${e(branch?.name || chosen.pharmacy__name || "Аптека")}</span><h3>${money(chosen.unit_price)}</h3><p>Доступно: <b>${Number(chosen.available)}</b> шт.</p><p class="muted">${e(branch ? `${branch.address}, ${branch.city}` : "Самовивіз або доставка з цієї аптеки")}</p></div>${addCartControl(p.id, p.name, "button primary add-to-cart product-add", chosen.pharmacy_id)}</div>` : empty("Немає в наявності", "Перегляньте інші позиції каталогу або перевірте аптеки пізніше.");
  return `<section class="content product-detail"><a class="back-link" href="#home">← Назад до каталогу</a><div class="detail-grid"><div class="detail-art tone-1">${image.url ? `<img class="detail-photo" src="${e(image.url)}" alt="${e(p.name)}" onerror="this.hidden=true">` : `<span class="bottle large"></span>`}<span class="product-tag ${p.prescription_required ? "prescription-label" : "otc-label"}">${p.prescription_required ? "ЗА РЕЦЕПТОМ" : "БЕЗ РЕЦЕПТА"}</span></div><div>${sectionHead("ІНФОРМАЦІЯ ПРО ТОВАР", e(p.name))}<p class="lead">${e(p.description || "Фармацевтичний препарат або товар для здоров’я.")}</p><p class="muted">${e(listOf(categories.value).find((x) => x.id === p.category)?.name || "")} · ${e(listOf(manufacturers.value).find((x) => x.id === p.manufacturer)?.name || "")}</p><p class="muted">Артикул: ${e(p.sku)}</p>${image.source ? `<p class="fine-print">Зображення товару: <a href="${e(image.source)}" target="_blank" rel="noopener noreferrer">джерело</a></p>` : ""}${p.storage_min_c !== null || p.storage_max_c !== null ? `<p class="muted">Умови зберігання з каталогу: ${e(p.storage_min_c ?? "—")}°C – ${e(p.storage_max_c ?? "—")}°C</p>` : ""}${p.prescription_required ? `<div class="notice info inline">Для цього товару потрібен рецепт. Наявність і правила оформлення перевірить API аптеки.</div>` : ""}<div class="availability-heading" id="availability"><div><p class="eyebrow">ЦІНА ТА НАЯВНІСТЬ</p><h2>Знайти в аптеках</h2></div><a class="button secondary" href="#pharmacies">Усі аптеки</a></div>${availabilityError ? `<div class="notice error inline">${e(availabilityError.message)}</div>` : available.length ? `<label class="field pharmacy-choice"><span>Оберіть аптеку</span><select data-action="product-pharmacy">${available.map((x) => { const item = pharmacyById.get(Number(x.pharmacy_id)); return `<option value="${x.pharmacy_id}" ${String(x.pharmacy_id) === String(chosen.pharmacy_id) ? "selected" : ""}>${e(item?.name || x.pharmacy__name)} — ${e(item?.address || "")}, ${e(item?.city || "")}</option>`; }).join("")}</select></label>${stockCard}` : stockCard}${currentUser?.role === "CUSTOMER" && available.length ? `<label class="field"><span>Аптека для сповіщення</span><select id="watch-pharmacy">${available.map((a) => `<option value="${a.pharmacy_id}">${e(pharmacyById.get(Number(a.pharmacy_id))?.name || a.pharmacy__name)}</option>`).join("")}</select></label>${button("Стежити за наявністю", "watch-product", "secondary", `data-id="${p.id}"`)}` : currentUser?.role !== "CUSTOMER" ? `<p class="fine-print">Увійдіть як клієнт, щоб стежити за наявністю.</p>` : ""}<p class="fine-print">Показані ціни й залишки належать вибраній аптеці. Для заявки обираються товари лише з однієї аптеки.</p></div></div></section>`;
}

async function pharmaciesPage() {
  const [data, assets] = await Promise.all([api.listAll("/pharmacies/", { auth: false }), branchAssets()]);
  return `<section class="content">${sectionHead("АПТЕКИ ПОРУЧ", "Оберіть аптеку", "Перейдіть у картку філії, щоб переглянути наявні препарати й оформити одне замовлення з неї.")}<div class="location-grid">${listOf(data).map((p, i) => { const sourceAsset = assets.get(p.code); const asset = { image_url: p.image_url || sourceAsset?.image_url, source_url: p.image_source_url || sourceAsset?.source_url }; return `<article class="location-card pharmacy-card" data-pharmacy-card data-route="pharmacy:${p.id}" role="link" tabindex="0" aria-label="Відкрити ${e(p.name)}, ${e(p.address)}"><div class="location-art art-${i % 3}">${asset?.image_url ? `<img src="${e(asset.image_url)}" alt="Філія ${e(p.name)}" loading="lazy" onerror="this.hidden=true">` : `<span>⌂</span>`}<small>${e(p.city)}</small></div><div class="location-body"><p class="eyebrow">${e(p.code)}</p><h2><a href="#pharmacy:${p.id}">${e(p.name)}</a></h2><p>${e(p.address)}, ${e(p.city)}</p><p>Довідкова мережі: ${e(p.phone || "уточніть на сторінці філії")}</p>${asset?.source_url ? `<a class="fine-print source-link" href="${e(asset.source_url)}" target="_blank" rel="noopener noreferrer">Фото й адресу звірити з офіційною сторінкою ↗</a>` : ""}<button class="button primary full" data-action="select-pharmacy" data-id="${p.id}">Обрати аптеку й товари →</button></div></article>`; }).join("") || empty("Аптек не знайдено", "Перевірте пізніше.")}</div></section>`;
}

async function pharmacyPage(id) {
  await choosePharmacy(id);
  const [pharmacy, inventoryData, productData, assets, images] = await Promise.all([api.request(`/pharmacies/${encodeURIComponent(id)}/`, { auth: false }), api.request(`/pharmacies/${encodeURIComponent(id)}/inventory/`, { auth: false }), api.request("/products/", { auth: false }), branchAssets(), productAssets()]);
  const inventory = listOf(inventoryData).filter((x) => Number(x.available) > 0);
  const products = new Map(listOf(productData).map((x) => [Number(x.id), x]));
  const sourceAsset = assets.get(pharmacy.code);
  const asset = { image_url: pharmacy.image_url || sourceAsset?.image_url, source_url: pharmacy.image_source_url || sourceAsset?.source_url };
  const rows = inventory.map((item) => { const product = products.get(Number(item.product_id)); if (!product) return ""; const image = productImage(product, images); return `<article class="product-card" data-product-card data-route="product:${product.id}" role="link" tabindex="0" aria-label="Переглянути ${e(product.name)}"><a class="product-image tone-${Number(product.id) % 4}" href="#product:${product.id}">${image.url ? `<img class="product-photo" src="${e(image.url)}" alt="${e(product.name)}" loading="lazy" onerror="this.hidden=true">` : `<span class="bottle"></span>`}<span class="product-tag ${product.prescription_required ? "prescription-label" : "otc-label"}">${product.prescription_required ? "ЗА РЕЦЕПТОМ" : "БЕЗ РЕЦЕПТА"}</span></a><div class="product-info"><p class="product-meta">Доступно ${Number(item.available)} шт.</p><h3><a href="#product:${product.id}">${e(product.name)}</a></h3><p class="product-description">${e(product.description || "Зарезервуйте товар у вибраній філії.")}</p><div class="product-foot"><strong class="branch-price">${money(item.unit_price)}</strong>${addCartControl(product.id, product.name, "button primary add-to-cart", pharmacy.id)}</div></div></article>`; }).filter(Boolean);
  return `<section class="content pharmacy-detail"><a class="back-link" href="#pharmacies">← До списку аптек</a><div class="branch-hero">${asset?.image_url ? `<img src="${e(asset.image_url)}" alt="Філія ${e(pharmacy.name)}" onerror="this.hidden=true">` : `<span class="branch-icon">⌂</span>`}<div><p class="eyebrow">КАРТКА АПТЕКИ</p><h1>${e(pharmacy.name)}</h1><p>${e(pharmacy.address)}, ${e(pharmacy.city)}</p><p>Довідкова мережі: ${e(pharmacy.phone || "—")}</p>${asset?.source_url ? `<a class="button secondary" href="${e(asset.source_url)}" target="_blank" rel="noopener noreferrer">Офіційна сторінка філії ↗</a>` : ""}</div></div><div class="section-head branch-products-head"><div><p class="eyebrow">НАЯВНІСТЬ У ЦІЙ ФІЛІЇ</p><h2>Обирайте товари для одного замовлення</h2><p class="muted">Кошик прив’язується до цієї аптеки. Ціна показана для цієї філії.</p></div><strong class="result-note">${rows.length} товарів у наявності</strong></div><div class="product-grid">${rows.length ? rows.join("") : empty("Немає товарів у наявності", "Перевірте іншу аптеку зі списку.")}</div><p class="fine-print data-disclosure">Навчальна система бронювання. Адреси та фото філій наведені з відкритих сторінок мережі; ціни, залишки й підтвердження замовлень у системі є імітованими.</p></section>`;
}

async function cartPage() {
  if (currentUser && currentUser.role !== "CUSTOMER") return `<section class="content narrow">${sectionHead("YOUR BAG", "Кошик клієнта", "Кошик доступний лише гостьовому або клієнтському сеансу.")}${card(`<p>Вийдіть з облікового запису або увійдіть як клієнт, щоб працювати з кошиком.</p><button class="button secondary" data-action="logout">Вийти</button>`)}</section>`;
  const guest = !auth.token;
  const cart = await api.request(guest ? "/guest-cart/" : "/cart/", { auth: !guest });
  let items = cart.items || [];
  if (!Array.isArray(items)) items = Object.entries(items).map(([product_id, quantity]) => ({ product_id: Number(product_id), quantity }));
  const [productsData, pharmaciesData, payments, loyalty] = await Promise.all([api.request("/products/", { auth: currentUser?.role === "ADMIN" }), api.listAll("/pharmacies/", { auth: false }), api.request("/payment-methods/", { auth: false }), currentUser ? api.request("/loyalty/").catch(() => ({ account: null })) : Promise.resolve({ account: null })]);
  const loyaltyBalance = Number(loyalty.account?.balance || 0);
  const products = listOf(productsData), pharmacies = listOf(pharmaciesData);
  if (!pharmacies.some((x) => String(x.id) === String(selectedPharmacyId))) selectedPharmacyId = String(pharmacies[0]?.id || "");
  const branchMap = readCartBranches();
  const itemsByPharmacy = new Map();
  for (const item of items) {
    const branchId = String(branchMap[item.product_id] || selectedPharmacyId || "");
    if (!branchId) continue;
    if (!branchMap[item.product_id]) branchMap[item.product_id] = branchId;
    if (!itemsByPharmacy.has(branchId)) itemsByPharmacy.set(branchId, []);
    itemsByPharmacy.get(branchId).push(item);
  }
  writeCartBranches(branchMap);
  const batches = await Promise.all([...itemsByPharmacy].map(async ([branchId, branchItems]) => {
    const branch = pharmacies.find((x) => String(x.id) === branchId);
    if (!branch) return null;
    let stockRows = [];
    try { stockRows = listOf(await api.request(`/pharmacies/${encodeURIComponent(branchId)}/inventory/`, { auth: false })); }
    catch { /* Keep the cart visible; the API remains authoritative at quote time. */ }
    const stock = new Map(stockRows.map((row) => [Number(row.product_id), row]));
    const availableItems = branchItems.filter((item) => Number(stock.get(Number(item.product_id))?.available || 0) > 0);
    const unavailableItems = branchItems.filter((item) => !availableItems.includes(item));
    let knownSubtotal = 0;
    let unknownPriceCount = 0;
    const makeRows = (entries, available) => entries.map((item) => {
      const product = products.find((x) => Number(x.id) === Number(item.product_id));
      const stockItem = stock.get(Number(item.product_id));
      const itemName = product?.name || `Товар №${item.product_id}`;
      const unitPrice = Number(stockItem?.unit_price);
      if (Number.isFinite(unitPrice) && unitPrice > 0) knownSubtotal += unitPrice * Number(item.quantity || 0);
      else unknownPriceCount += 1;
      return `<tr class="${available ? "" : "cart-item-unavailable"}"><td><b>${e(itemName)}</b><small>${e(product?.sku || "")}</small>${available ? "" : `<small class="unavailable-note">Немає підтвердженої наявності у цій філії. Видаліть позицію або оберіть іншу аптеку.</small>`}</td><td><div class="cart-product-price"><span>ЦІНА ПРЕПАРАТУ</span><strong>${Number.isFinite(unitPrice) && unitPrice > 0 ? money(unitPrice) : "ЦІНУ НЕ ЗНАЙДЕНО"}</strong></div></td><td><div class="quantity-control"><button class="quantity-step" type="button" data-action="quantity-minus" data-id="${item.product_id}" aria-label="Зменшити кількість: ${e(itemName)}">−</button><input class="quantity-input" type="number" min="0" max="10000" value="${item.quantity}" data-quantity="${item.product_id}" aria-label="Кількість: ${e(itemName)}"><button class="quantity-step" type="button" data-action="quantity-plus" data-id="${item.product_id}" aria-label="Збільшити кількість: ${e(itemName)}">+</button></div></td><td><button class="text-button danger-text" data-action="remove" data-id="${item.product_id}">Видалити</button></td></tr>`;
    });
    const paymentMethods = payments.methods || [];
    const initialMethod = paymentMethods.includes("CARD") ? "CARD" : (paymentMethods.includes("ONLINE_GATEWAY") ? "ONLINE_GATEWAY" : (paymentMethods[0] || ""));
    const cardFieldsInitiallyVisible = ["CARD", "ONLINE_GATEWAY"].includes(initialMethod) && !guest;
    const cardPaymentFields = `<div class="cart-demo-card-fields ${cardFieldsInitiallyVisible ? "" : "hidden"}" data-cart-demo-card-fields><p class="demo-payment-banner"><b>DEMO PAYMENT — NO REAL MONEY</b><br>Лише вигадані реквізити для навчальної симуляції. Реальні картки не приймаються; кошти не переказуються.</p>${guest ? `<p class="fine-print">Увійдіть як покупець, щоб увести тестові дані.</p>` : `<p class="demo-credentials">Тестові значення: <code>DEMO USER</code> · <code>0000 0000 0000 0000</code> · <code>12/30</code> · <code>000</code></p><label class="field"><span>Ім’я на картці</span><input name="demo_cardholder" autocomplete="off" maxlength="30" ${cardFieldsInitiallyVisible ? "required" : "disabled"}></label><label class="field"><span>Номер тестової картки</span><input name="demo_card_number" inputmode="numeric" autocomplete="off" maxlength="23" ${cardFieldsInitiallyVisible ? "required" : "disabled"}></label><div class="demo-card-row"><label class="field"><span>Строк дії (MM/YY)</span><input name="demo_expiry" inputmode="numeric" autocomplete="off" maxlength="5" ${cardFieldsInitiallyVisible ? "required" : "disabled"}></label><label class="field"><span>CVV</span><input name="demo_cvv" inputmode="numeric" autocomplete="off" maxlength="3" ${cardFieldsInitiallyVisible ? "required" : "disabled"}></label></div><label class="field"><span>Результат симуляції</span><select name="demo_scenario" ${cardFieldsInitiallyVisible ? "" : "disabled"}><option value="APPROVED">APPROVED — схвалити</option><option value="DECLINED">DECLINED — відхилити</option><option value="TIMEOUT">TIMEOUT — очікування/тайм-аут</option></select></label><p class="notice error inline hidden" data-cart-card-error role="alert"></p>`}</div>`;
    const form = availableItems.length ? `<form class="batch-checkout" data-form="checkout"><input type="hidden" name="pharmacy_id" value="${e(branch.id)}"><input type="hidden" name="product_ids" value="${availableItems.map((x) => Number(x.product_id)).join(",")}"><label class="field bonus-redemption"><span>Використати бонуси (1 бонус = 1 грн)</span><input name="redeem_points" type="number" min="0" max="${loyaltyBalance}" value="0" step="1" ${currentUser ? "" : "disabled"}></label><p class="fine-print bonus-balance-note">Доступно: ${loyaltyBalance} бонусів. Ними можна покрити до половини вартості товарів після знижок; доставка оплачується окремо.</p>${selectField("Спосіб отримання", "fulfillment_method", [["PICKUP", "Самовивіз у цій аптеці"], ["COURIER", "Кур’єрська доставка"], ["POSTAL", "Поштова доставка"]], true)}${selectField("Спосіб оплати", "payment_method", (payments.methods || []).map((x) => [x, paymentMethod(x)]), true)}${cardPaymentFields}<div class="form-group recipient-fields hidden">${field("Ім’я отримувача", "recipient_name", "text", false)}${field("Телефон отримувача", "recipient_phone", "tel", false)}${field("Адреса доставки", "recipient_destination", "text", false)}</div><button class="button primary checkout-cta" type="submit">${guest ? "Увійдіть, щоб оформити це замовлення" : `Оформити замовлення з аптеки ${e(branch.name)}`} <span>→</span></button><p class="fine-print">Це замовлення оформлюється окремо від інших аптек.</p></form>` : `<p class="notice error inline">У цій групі немає товарів із підтвердженою наявністю для оформлення.</p>`;
    const allRows = [...makeRows(availableItems, true), ...makeRows(unavailableItems, false)];
    const html = `<section class="cart-batch"><div class="cart-batch-heading"><div><p class="eyebrow">ОКРЕМЕ ЗАМОВЛЕННЯ · ${availableItems.length} ДОСТУПНО</p><h2>${e(branch.name)}</h2><p>${e(branch.address)}, ${e(branch.city)}</p></div><a class="text-button" href="#pharmacy:${branch.id}">Переглянути аптеку ↗</a></div>${card(`${table(["ТОВАР", "ЦІНА", "КІЛЬКІСТЬ", ""], allRows)}<div class="cart-actions"><button class="button secondary" data-action="update-cart">Оновити кількість</button><a class="button secondary continue-shopping" href="#catalog">← Продовжити покупки</a><div class="cart-batch-total" aria-live="polite"><span>Сума замовлення</span><strong>${money(knownSubtotal)}</strong><small>${unknownPriceCount ? "Сума неповна: ціни частини товарів недоступні." : "Вартість товарів без доставки та знижок."}</small></div></div>`)}${form}</section>`;
    return { html, knownSubtotal, unknownPriceCount };
  }));
  const visibleBatches = batches.filter(Boolean);
  const knownCartTotal = visibleBatches.reduce((total, batch) => total + batch.knownSubtotal, 0);
  const unknownPriceCount = visibleBatches.reduce((total, batch) => total + batch.unknownPriceCount, 0);
  const cartTotalSummary = visibleBatches.length ? `<div class="cart-total-summary"><div><span>ЗАГАЛЬНА СУМА ВСІХ ПОКУПОК</span><strong>${money(knownCartTotal)}</strong></div><p>${unknownPriceCount ? `Не вдалося отримати ціну для ${unknownPriceCount} позицій. Остаточну суму підтвердить сервер під час оформлення.` : "Сума попередня; остаточну вартість сервер підтвердить під час оформлення."}</p></div>` : "";
  return `<section class="content">${sectionHead("ВАШ КОШИК", "Вдалий вибір.", "Товари з різних аптек згруповані в окремі замовлення. Кожне має власний шлях оформлення.")}${cartTotalSummary}${visibleBatches.length ? `<div class="cart-batches">${visibleBatches.map((batch) => batch.html).join("")}</div>` : card(empty("Кошик порожній", "Додайте товари з каталогу."))}<p class="fine-print">${guest ? "Гостьовий кошик зберігається API в cookie браузера." : "Кошик пов’язаний з обліковим записом клієнта."} Оплата та доставка імітовані.</p></section>`;
}

function authPage(route) {
  if (currentUser) return `<section class="content narrow">${sectionHead("ВІТАЄМО", `Ви увійшли як ${e(currentUser.username)}`)}${card(`<p>Тип облікового запису: <b>${e(({ CUSTOMER: "Клієнт", STAFF: "Працівник аптеки", ADMIN: "Адміністратор" })[currentUser.role] || currentUser.role)}</b></p><a class="button primary" href="#${"account"}">Перейти до кабінету</a>`)}</section>`;
  return `<section class="auth-layout"><div class="auth-visual"><p class="eyebrow">ІНТЕРНЕТ-АПТЕКА GOODWELL</p><h1>Турбота починається<br>зі <em>знайомства.</em></h1><p>Увійдіть, щоб керувати профілем і замовленнями.</p></div><div class="auth-form-wrap">${route === "login" ? `<p class="eyebrow">ОБЛІКОВИЙ ЗАПИС</p><h1>З поверненням</h1><p class="muted">Введіть ім’я користувача та пароль.</p><form data-form="login">${field("Ім’я користувача", "username", "text", true)}${field("Пароль", "password", "password", true)}<button class="button primary full" type="submit">Увійти <span>→</span></button></form><p class="switch-auth">Ще не зареєстровані? <a href="#register">Створити обліковий запис</a></p>` : `<p class="eyebrow">РЕЄСТРАЦІЯ</p><h1>Створити обліковий запис</h1><p class="muted">Новий обліковий запис буде клієнтським.</p><form data-form="register">${field("Повне ім’я", "full_name", "text", true)}${field("Електронна пошта", "email", "email", true)}${field("Ім’я користувача", "username", "text", true)}<label class="field"><span>Пароль (не менше 4 символів)</span><input name="password" type="password" minlength="4" maxlength="128" required autocomplete="new-password"></label><button class="button primary full" type="submit">Зареєструватися <span>→</span></button></form><p class="switch-auth">Вже маєте обліковий запис? <a href="#login">Увійти</a></p>`}</div></section>`;
}

async function accountPage() {
  if (!currentUser) return signedOut();
  if (currentUser.role !== "CUSTOMER") return `<section class="content narrow">${sectionHead("ACCOUNT", "This area is for customers")}</section>`;
  const responses = await Promise.allSettled([
    api.request("/profile/"), api.request("/preferences/"), api.request("/loyalty/"), api.request("/notifications/"), api.request("/reminders/"), api.request("/availability-watches/"), api.request("/prescriptions/"),
    api.listAll("/pharmacies/", { auth: false }), api.request("/orders/"), api.request("/products/", { auth: false }),
  ]);
  const names = ["Profile", "notification preferences", "loyalty", "notifications", "reminders", "availability watches", "saved prescriptions", "pharmacies", "orders", "products"];
  const loadFailures = responses.flatMap((result, index) => result.status === "rejected" ? [`${names[index]}: ${result.reason.message}`] : []);
  const [profile, preferences, loyalty, notifications, reminders, watches, prescriptions, pharmaciesData, orders, productData] = responses.map((result) => result.status === "fulfilled" ? result.value : {});
  const prefs = listOf(preferences)[0] || {};
  const pharmacyOptions = [["", "No preference"], ...listOf(pharmaciesData).map((p) => [p.id, p.name])];
  const profileCard = card(`<p class="eyebrow">PROFILE</p><h2>Your details</h2><form data-form="profile">${field("Full name", "full_name", "text", true, profile.full_name)}${field("Phone", "phone", "tel", false, profile.phone || "")}${selectField("Preferred pharmacy", "preferred_pharmacy_id", pharmacyOptions)}<button class="button secondary" type="submit">Save details</button></form>`);
  const prescriptionsTable = listOf(prescriptions).length
    ? table(["LABEL", "REFERENCE", ""], listOf(prescriptions).map((x) => `<tr><td>${e(x.display_label)}</td><td>${e(x.masked_reference)}</td><td><button class="text-button danger-text" data-action="delete-prescription" data-id="${x.id}">Remove</button></td></tr>`))
    : empty("Nothing saved", "Add a label to help identify your prescription record.");
  const careCard = card(`<p class="eyebrow">YOUR CARE</p><h2>Saved prescriptions</h2>${prescriptionsTable}<form class="inline-form" data-form="prescription">${field("Display label", "display_label", "text", true)}<button class="button secondary" type="submit">Add label</button></form><p class="fine-print">Only a masked reference is stored here, not a prescription image or medical document.</p>`);
  const activeTier = loyalty.account?.tier__code || "STANDARD";
  const premiumStatusCopy = ({ SUCCEEDED: "Оплату симуляції схвалено", FAILED: "Попередню симуляцію оплати відхилено", UNKNOWN: "Результат симуляції очікує уточнення", NOT_PAID: "Оплату ще не виконано" })[loyalty.account?.premium_payment_status || "NOT_PAID"];
  const loyaltyCard = card(`<p class="eyebrow">ЛОЯЛЬНІСТЬ</p><h2>${e(({ STANDARD: "Стандартна", SOCIAL: "Соціальна", PREMIUM: "Premium" })[activeTier] || activeTier)}</h2><p class="points">${e(loyalty.account?.balance ?? 0)} <small>бонусів · 1 бонус = 1 грн</small></p><p class="fine-print">Бонусний рахунок використовується для часткової оплати замовлення. Оберіть програму лояльності:</p><form data-form="loyalty-tier" data-current-tier="${e(activeTier)}"><label class="field"><span>Система лояльності</span><select name="tier"><option value="STANDARD" ${activeTier === "STANDARD" ? "selected" : ""}>Стандартна — без оплати</option><option value="SOCIAL" ${activeTier === "SOCIAL" ? "selected" : ""}>Соціальна — підтвердження документа</option><option value="PREMIUM" ${activeTier === "PREMIUM" ? "selected" : ""}>Premium — ${money(loyalty.account?.premium_monthly_price || 30)} / місяць</option></select></label><div class="loyalty-social-fields ${activeTier === "SOCIAL" ? "" : "hidden"}" data-loyalty-social-fields><label class="field"><span>Номер документа (6 цифр)</span><input name="document_number" inputmode="numeric" autocomplete="off" pattern="[0-9]{6}" minlength="6" maxlength="6" value="${e(loyalty.account?.social_document_number || "")}" ${activeTier === "SOCIAL" ? "required" : "disabled"}></label><p class="fine-print">Номер використовується лише для цього облікового запису.</p></div><div class="cart-demo-card-fields loyalty-premium-fields ${activeTier === "PREMIUM" ? "" : "hidden"}" data-loyalty-premium-fields><p class="demo-payment-banner"><b>DEMO PAYMENT — NO REAL MONEY</b><br>Тестова картка для оплати підписки Premium: ${money(loyalty.account?.premium_monthly_price || 30)} за 30 днів. Реквізити не передаються API і не зберігаються.</p><p class="demo-credentials">Тестові значення: <code>DEMO USER</code> · <code>0000 0000 0000 0000</code> · <code>12/30</code> · <code>000</code></p><label class="field"><span>Ім’я на картці</span><input name="premium_cardholder" autocomplete="off" maxlength="30" ${activeTier === "PREMIUM" ? "required" : "disabled"}></label><label class="field"><span>Номер тестової картки</span><input name="premium_card_number" inputmode="numeric" autocomplete="off" maxlength="23" ${activeTier === "PREMIUM" ? "required" : "disabled"}></label><div class="demo-card-row"><label class="field"><span>Строк дії (MM/YY)</span><input name="premium_expiry" inputmode="numeric" autocomplete="off" maxlength="5" ${activeTier === "PREMIUM" ? "required" : "disabled"}></label><label class="field"><span>CVV</span><input name="premium_cvv" inputmode="numeric" autocomplete="off" maxlength="3" ${activeTier === "PREMIUM" ? "required" : "disabled"}></label></div><label class="field"><span>Результат симуляції</span><select name="demo_scenario" ${activeTier === "PREMIUM" ? "" : "disabled"}><option value="APPROVED">APPROVED — схвалити</option><option value="DECLINED">DECLINED — відхилити</option><option value="TIMEOUT">TIMEOUT — очікування / тайм-аут</option></select></label><p class="fine-print" data-premium-payment-status>${e(premiumStatusCopy)}${loyalty.account?.premium_active_until ? ` · Підписка активна до ${e(new Date(loyalty.account.premium_active_until).toLocaleDateString("uk-UA"))}` : ""}</p><p class="notice error inline hidden" data-loyalty-card-error role="alert"></p></div><button class="button secondary" type="submit">${activeTier === "PREMIUM" && loyalty.account?.premium_status === "ACTIVE" ? "Оплатити наступний місяць" : "Зберегти програму"}</button></form>${listOf(loyalty.transactions).length ? `<details><summary>Останні операції бонусного рахунку</summary><ul>${listOf(loyalty.transactions).slice(0, 5).map((x) => { const delta = Number(x.points_delta ?? x.points ?? x.amount); return `<li>${e(x.type || x.transaction_type || "Операція")}: ${Number.isFinite(delta) ? `${delta > 0 ? "+" : ""}${e(delta)}` : "—"} бонусів</li>`; }).join("")}</ul></details>` : ""}<a href="#orders" class="text-button">Переглянути замовлення →</a>`);
  const preferencesCard = card(`<p class="eyebrow">PREFERENCES</p><h2>Keep in touch</h2><form data-form="preferences"><label class="check-row"><input type="checkbox" name="promotions_enabled" ${prefs.promotions_enabled ? "checked" : ""}> Pharmacy offers</label><label class="check-row"><input type="checkbox" name="reminders_enabled" ${prefs.reminders_enabled ? "checked" : ""}> Order reminders</label><button class="button secondary" type="submit">Save preferences</button></form>`);
  const notificationRows = listOf(notifications).slice(0, 6).map((x) => `<li><b>${e(x.title || x.kind || "Update")}</b><small>${e(x.body || x.message || "Pharmacy update")}</small>${!x.read_at ? `<button class="text-button" data-action="read-notification" data-id="${x.id}">Mark read</button>` : ""}</li>`).join("");
  const notificationCard = card(`<p class="eyebrow">NOTIFICATIONS</p><h2>Recent updates</h2>${notificationRows ? `<ul class="feed-list">${notificationRows}</ul>` : empty("All caught up", "New account notifications will appear here.")}`);
  const reminderRows = listOf(reminders).map((x) => `<li>Product ${x.product_id} · every ${x.interval_days} days</li>`).join("");
  const watchTable = listOf(watches).length ? table(["ТОВАР", "АПТЕКА", "СТАН", ""], listOf(watches).map((x) => `<tr><td>${e(x.product_id)}</td><td>${e(x.pharmacy_id)}</td><td>${x.is_active ? "Активне" : "Призупинено"}</td><td><button class="text-button" data-action="toggle-watch" data-product="${x.product_id}" data-pharmacy="${x.pharmacy_id}" data-active="${x.is_active}">${x.is_active ? "Призупинити" : "Відновити"}</button></td></tr>`)) : empty("Немає підписок", "Увімкніть сповіщення про наявність на сторінці товару.");
  const productOptions = listOf(productData).map((x) => [x.id, `${x.name} · ${x.sku}`]);
  const carePlanCard = card(`<p class="eyebrow">НАГАДУВАННЯ І НАЯВНІСТЬ</p><h2>Стеження за наявністю</h2>${watchTable}<h3>Нагадування</h3>${reminderRows ? `<ul>${reminderRows}</ul>` : `<p class="muted">Нагадувань поки немає.</p>`}<form class="inline-form" data-form="reminder">${selectField("Товар", "product_id", productOptions, true)}${field("Інтервал (днів)", "interval_days", "number", true, 30)}${field("Наступна дата", "next_run_at", "datetime-local", true)}<button class="button secondary" type="submit">Додати нагадування</button></form><p class="fine-print">Час наступного нагадування має бути в майбутньому.</p>`);
  const recentOrders = listOf(orders).slice(0, 3);
  const orderSummary = card(`<p class="eyebrow">ОСТАННІ ЗАМОВЛЕННЯ</p><h2>Ваші покупки</h2>${recentOrders.length ? `<ul>${recentOrders.map((x) => `<li>№ ${e(x.order_number || x.id)} · ${e(orderStatus(x.status))} · ${money(x.grand_total, x.currency)}</li>`).join("")}</ul>` : `<p class="muted">Замовлень поки немає.</p>`}<a class="text-button" href="#orders">Переглянути всі замовлення →</a>`);
  return `<section class="content">${sectionHead("МІЙ КАБІНЕТ", `Вітаємо, ${e(profile.full_name || currentUser.username)}`, "Профіль, замовлення, налаштування та бонусна програма.")}${loadFailures.length ? `<div class="notice error inline">Не вдалося завантажити частину даних API: ${e(loadFailures.join(" · "))}</div>` : ""}<div class="account-tabs">${navLink("Огляд", "account", true)}${navLink("Замовлення", "orders", false)}${navLink("Кошик", "cart", false)}</div>${orderSummary}<div class="account-grid"><div>${profileCard}${careCard}</div><div>${loyaltyCard}${preferencesCard}${notificationCard}${carePlanCard}</div></div></section>`;
}

function signedOut() { return `<section class="content narrow">${sectionHead("МІЙ КАБІНЕТ", "Увійдіть, щоб продовжити")}${card(`<p class="muted">Керуйте замовленнями, профілем і програмою лояльності.</p><a class="button primary" href="#login">Увійти</a> <a href="#register" class="text-button">Створити обліковий запис</a>`)}</section>`; }

async function ordersPage() {
  if (!currentUser) return signedOut();
  if (currentUser.role !== "CUSTOMER") return `<section class="content narrow">${sectionHead("ЗАМОВЛЕННЯ", "Перегляд доступний клієнтам")}${card(`<p>Для роботи із замовленнями аптеки відкрийте робочий кабінет.</p><a class="button primary" href="#login">Увійти як покупець</a>`)}</section>`;
  const data = await api.request("/orders/");
  const orders = listOf(data);
  const pharmacies = await api.listAll("/pharmacies/", { auth: false }).catch(() => []);
  const pharmacyById = new Map(listOf(pharmacies).map((branch) => [String(branch.id), branch]));
  const pharmacyDetails = (order) => {
    const branch = pharmacyById.get(String(order.pharmacy_id));
    return `<div class="order-pharmacy"><p class="eyebrow">${order.fulfillment_method === "PICKUP" ? "АПТЕКА ДЛЯ САМОВИВОЗУ" : "АПТЕКА, ЩО ВИКОНУЄ ЗАМОВЛЕННЯ"}</p><strong>${e(branch?.name || `Аптека №${order.pharmacy_id}`)}</strong><p>${e(branch ? [branch.address, branch.city].filter(Boolean).join(", ") : "Адреса аптеки тимчасово недоступна")}</p>${branch ? `<a class="button secondary" href="#pharmacy:${e(branch.id)}">Переглянути аптеку →</a>` : ""}</div>`;
  };
  const traces = await Promise.all(orders.map((o) => api.request(`/orders/${o.id}/fulfillment/`).catch((error) => ({ error: error.message }))));
  return `<section class="content">${sectionHead("МІЙ КАБІНЕТ", "Історія замовлень", "Перегляд замовлень, стану оплати та доставки.")}<div class="account-tabs">${navLink("Огляд", "account", false)}${navLink("Замовлення", "orders", true)}${navLink("Кошик", "cart", false)}</div>${orders.length ? `<div class="order-list">${orders.map((o, index) => { const trace = traces[index]; const hasPayment = trace.payments?.length > 0; const canPay = ["CARD", "ONLINE_GATEWAY"].includes(o.payment_method) && !["CANCELLED", "COMPLETED"].includes(o.status) && !hasPayment && !trace.error; return `<article class="order-card"><div class="order-head"><div><p class="eyebrow">ЗАМОВЛЕННЯ ${e(o.order_number || o.id)}</p><h2>${e(orderStatus(o.status))}</h2></div><strong>${money(o.grand_total, o.currency)}</strong></div><p class="muted">${e(({ PICKUP: "Самовивіз", COURIER: "Кур’єрська доставка", POSTAL: "Поштова доставка" })[o.fulfillment_method] || o.fulfillment_method)} · ${new Date(o.created_at).toLocaleDateString("uk-UA")}</p>${pharmacyDetails(o)}<div class="order-items">${(o.items || []).map((i) => `<span>${e(i.product_name_snapshot)} × ${i.quantity}</span>`).join("")}</div>${trace.error ? `<p class="notice error inline">Дані платежу/доставки тимчасово недоступні: ${e(trace.error)}</p>` : `<div class="order-tracking"><b>Оплата:</b> ${e(trace.payments?.map((x) => `${orderStatus(x.status)} (${x.provider}, ${money(x.amount)})`).join(" · ") || "ще не ініційована")}<br><b>Доставка:</b> ${e(trace.delivery ? `${orderStatus(trace.delivery.status)}${trace.delivery.tracking_reference ? ` · ${trace.delivery.tracking_reference}` : ""}` : "не створена")}<br><b>Повернення:</b> ${e(trace.refunds?.map((x) => `${orderStatus(x.status)} ${money(x.amount)}`).join(" · ") || "немає")}</div>`}<div class="order-actions">${o.cancellation_reason_code ? `<p class="order-cancellation-reason"><b>Причина скасування:</b> ${e(cancellationReasonLabel(o.cancellation_reason_code))}</p>` : ""}${canPay ? button("Оплатити", "pay", "secondary", `data-id="${o.id}"`) : ""}${["PENDING_CONFIRMATION", "PENDING_PAYMENT", "CONFIRMED"].includes(o.status) ? button("Скасувати замовлення", "cancel-order", "secondary", `data-id="${o.id}"`) : ""}${button("Замовити знову", "reorder", "text", `data-id="${o.id}`)}</div></article>`; }).join("")}</div>` : card(empty("Замовлень поки немає", "Ваші замовлення з’являться тут після оформлення."))}</section>`;
}

async function demoPaymentPage(orderId) {
  if (!currentUser) return signedOut();
  if (currentUser.role !== "CUSTOMER") return `<section class="content narrow">${sectionHead("ОПЛАТА", "Доступно клієнтам")}</section>`;
  const order = await api.request(`/orders/${encodeURIComponent(orderId)}/`);
  const trace = await api.request(`/orders/${order.id}/fulfillment/`);
  const payment = trace.payments?.slice().sort((a, b) => b.id - a.id)[0];
  const outcome = payment?.status === "SUCCEEDED"
    ? `<div class="demo-result approved" role="status"><h2>Оплату підтверджено</h2><p>Результат симуляції: APPROVED. Реального платежу не було.</p></div>`
    : payment?.status === "FAILED"
      ? `<div class="demo-result declined" role="status"><h2>Оплату відхилено</h2><p>Результат симуляції: DECLINED. Замовлення не оплачено.</p></div>`
      : payment?.status === "UNKNOWN"
        ? `<div class="demo-result pending" role="status"><h2>Результат невідомий</h2><p>Симулятор повернув TIMEOUT. Платіж збережено як такий, що очікує з’ясування; успішним він не позначений.</p></div>`
        : payment?.status === "PENDING"
          ? `<div class="demo-result pending" role="status"><h2>Платіж обробляється</h2><p>Оновіть сторінку за кілька секунд, щоб побачити результат.</p></div>`
          : "";
  const canStart = !payment && ["CARD", "ONLINE_GATEWAY"].includes(order.payment_method) && !["CANCELLED", "COMPLETED"].includes(order.status);
  return `<section class="content narrow demo-payment"><p class="eyebrow">БЕЗПЕЧНИЙ НАВЧАЛЬНИЙ СЦЕНАРІЙ</p><h1>DEMO PAYMENT — NO REAL MONEY</h1><p class="muted">Освітня симуляція. Реальні банківські картки не приймаються; гроші не переказуються.</p><div class="demo-order-summary"><b>Замовлення №${e(order.order_number || order.id)}</b><strong>${money(order.grand_total, order.currency)}</strong><span>Сума розрахована сервером · ${e(orderStatus(order.status))}</span></div>${outcome}${canStart ? `<form class="demo-payment-form" data-form="demo-payment" data-order-id="${e(order.id)}"><h2>Дані вигаданої тестової картки</h2><p class="demo-credentials">Номер: <code>0000 0000 0000 0000</code> · Строк: <code>12/30</code> · CVV: <code>000</code> · Ім’я: <code>DEMO USER</code></p><p class="fine-print">Інші значення, включно з реальними або схожими на реальні номерами, буде відхилено. Поля не надсилаються на сервер і не зберігаються.</p><label class="field"><span>Ім’я на картці</span><input name="cardholder" autocomplete="off" required maxlength="30"></label><label class="field"><span>Номер тестової картки</span><input name="card_number" inputmode="numeric" autocomplete="off" required maxlength="23" aria-describedby="demo-card-error"></label><div class="demo-card-row"><label class="field"><span>Строк дії (MM/YY)</span><input name="expiry" inputmode="numeric" autocomplete="off" required maxlength="5"></label><label class="field"><span>CVV</span><input name="cvv" inputmode="numeric" autocomplete="off" required maxlength="3"></label></div><label class="field"><span>Результат симуляції</span><select name="demo_scenario" required><option value="APPROVED">APPROVED — схвалити</option><option value="DECLINED">DECLINED — відхилити</option><option value="TIMEOUT">TIMEOUT — очікування/тайм-аут</option></select></label><p id="demo-card-error" class="notice error inline hidden" role="alert"></p><button class="button primary full" type="submit">Запустити симуляцію · ${money(order.grand_total, order.currency)}</button></form>` : !outcome ? `<div class="demo-result declined"><p>Це замовлення не можна оплатити через тестову картку. Перевірте спосіб оплати та стан замовлення.</p></div>` : ""}<a class="button secondary" href="#orders">Повернутися до замовлень</a></section>`;
}

async function submitDemoPayment(form) {
  const isFictional = isFictionalDemoCard({
    cardholder: form.elements.cardholder.value,
    card_number: form.elements.card_number.value,
    expiry: form.elements.expiry.value,
    cvv: form.elements.cvv.value,
  });
  const error = form.querySelector("#demo-card-error");
  if (!isFictional) {
    form.elements.cardholder.value = "";
    form.elements.card_number.value = "";
    form.elements.expiry.value = "";
    form.elements.cvv.value = "";
    error.textContent = "Реквізити не збігаються з вигаданою тестовою карткою. Реальні картки не підтримуються.";
    error.classList.remove("hidden");
    return;
  }
  const orderId = form.dataset.orderId;
  const scenario = form.elements.demo_scenario.value;
  const buttonEl = form.querySelector('[type="submit"]');
  buttonEl.disabled = true;
  buttonEl.textContent = "Симуляція обробляється…";
  form.reset();
  try {
    const keyStorage = `pharmacy.demoPaymentKey.${currentUser.id}.${orderId}`;
    let idempotencyKey = sessionStorage.getItem(keyStorage);
    if (!idempotencyKey) {
      idempotencyKey = crypto.randomUUID();
      sessionStorage.setItem(keyStorage, idempotencyKey);
    }
    await api.request(`/orders/${orderId}/pay/`, { method: "POST", body: demoPaymentRequestPayload(idempotencyKey, scenario) });
    let paymentStatus = "PENDING";
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline) {
      const trace = await api.request(`/orders/${orderId}/fulfillment/`);
      const latest = trace.payments?.slice().sort((a, b) => b.id - a.id)[0];
      paymentStatus = latest?.status || "PENDING";
      if (paymentStatus !== "PENDING") break;
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    flash(paymentStatus === "SUCCEEDED"
      ? "Результат симуляції: APPROVED. Замовлення позначено оплаченим у системі."
      : paymentStatus === "FAILED"
        ? "Результат симуляції: DECLINED. Оплату не підтверджено."
        : paymentStatus === "UNKNOWN"
          ? "Результат симуляції: TIMEOUT. Статус очікує з’ясування, оплата не підтверджена."
          : "Симуляція ще обробляється; результат з’явиться в історії замовлень.");
    render();
  } catch (submitError) {
    flash(submitError.message, "error");
    render();
  }
}

function authRequired() { return "Please sign in before continuing."; }

root.addEventListener("click", (event) => {
  const card = event.target.closest("[data-product-card], [data-pharmacy-card]");
  if (!card || event.target.closest("a,button,select,input")) return;
  location.hash = card.dataset.route;
});
root.addEventListener("keydown", (event) => {
  if (!["Enter", " "].includes(event.key)) return;
  const card = event.target.closest("[data-product-card], [data-pharmacy-card]");
  if (!card || event.target !== card) return;
  event.preventDefault();
  location.hash = card.dataset.route;
});

root.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]"); if (!target) return;
  const action = target.dataset.action;
  if (["logout", "remove", "update-cart", "quantity-minus", "quantity-plus", "cancel-order", "reorder", "pay", "transition", "ship", "verify-prescription", "refund", "read-notification", "delete-prescription", "watch-product", "toggle-watch", "edit-row", "confirm-order"].includes(action)) target.disabled = true;
  try {
    if (action === "reset-filters") {
      catalogFilters = { search: "", category: "", manufacturer: "", pharmacy: "" };
      catalogPageNumber = 1;
      render();
    }
    if (action === "dismiss") { message = ""; render(); }
    if (action === "confirm-order") { await confirmOrder(); }
    if (action === "back-to-cart") { pendingOrder = null; render(); }
    if (action === "retry") render();
    if (action === "next-page") { catalogPageNumber += 1; render(); }
    if (action === "previous-page") { catalogPageNumber = Math.max(1, catalogPageNumber - 1); render(); }
    if (action === "logout") { auth.clear(); currentUser = null; flash("You have signed out."); location.hash = "home"; render(); }
    if (action === "menu") document.querySelector(".main-nav")?.classList.toggle("open");
    if (action === "add") {
      await addOneToCart(Number(target.dataset.id), target.dataset.pharmacy);
      clearTimeout(addToCartNavigationTimer);
      addToCartNavigationTimer = setTimeout(() => {
        location.hash = "cart";
        render();
      }, 650);
    }
    if (action === "select-pharmacy") { await choosePharmacy(target.dataset.id); location.hash = `pharmacy:${target.dataset.id}`; }
    if (action === "remove") await changeCart(Number(target.dataset.id), 0);
    if (action === "quantity-minus" || action === "quantity-plus") {
      const input = target.closest(".quantity-control")?.querySelector("[data-quantity]");
      if (!input) throw new Error("Не вдалося знайти поле кількості товару.");
      const delta = action === "quantity-plus" ? 1 : -1;
      const quantity = Math.max(1, Math.min(10000, Number(input.value || 1) + delta));
      await changeCart(Number(target.dataset.id), quantity);
    }
    if (action === "update-cart") { for (const input of document.querySelectorAll("[data-quantity]")) await changeCart(Number(input.dataset.quantity), Number(input.value), "", false); flash("Кількість збережена в API."); render(); }
    if (action === "inventory") { const data = await api.request(`/pharmacies/${target.dataset.id}/inventory/`, { auth: false }); document.querySelector(`#stock-${target.dataset.id}`).innerHTML = listOf(data).map((x) => `<p>${e(x.product__name)} · ${x.available} available · ${money(x.unit_price)}</p>`).join("") || "No listed stock"; }
    if (action === "cancel-order") { if (!window.confirm("Скасувати замовлення? API може автоматично звільнити резерв товару та запустити повернення платежу.")) { target.disabled = false; return; } await api.request(`/orders/${target.dataset.id}/transition/`, { method: "POST", body: { status: "CANCELLED" } }); flash("Запит на скасування підтверджено сервером."); render(); }
    if (action === "reorder") { await api.request(`/orders/${target.dataset.id}/reorder/`, { method: "POST", body: {} }); flash("Items copied to your cart. Request a fresh quote before ordering."); location.hash = "cart"; render(); }
    if (action === "pay") { location.hash = `pay:${target.dataset.id}`; render(); }
    if (action === "fulfillment") { const data = await api.request(`/orders/${target.dataset.id}/fulfillment/`); const box = document.querySelector(`#fulfillment-${target.dataset.id}`); box.innerHTML = `<pre>${e(JSON.stringify(data, null, 2))}</pre>`; }
    if (action === "read-notification") { await api.request(`/notifications/${target.dataset.id}/read/`, { method: "POST", body: {} }); flash("Notification marked as read."); render(); }
    if (action === "delete-prescription") { if (!window.confirm("Видалити збережену позначку рецепта?")) { target.disabled = false; return; } await api.request(`/prescriptions/${target.dataset.id}/`, { method: "DELETE" }); flash("Позначку рецепта видалено."); render(); }
    if (action === "watch-product") { const pharmacyId = Number(document.querySelector("#watch-pharmacy")?.value); if (!pharmacyId) throw new Error("Для цього товару немає аптеки з відкритою наявністю."); await api.request("/availability-watches/", { method: "POST", body: { product_id: Number(target.dataset.id), pharmacy_id: pharmacyId, is_active: true } }); flash("Підписку наявності збережено через API."); render(); }
    if (action === "toggle-watch") { await api.request("/availability-watches/", { method: "POST", body: { product_id: Number(target.dataset.product), pharmacy_id: Number(target.dataset.pharmacy), is_active: target.dataset.active !== "true" } }); flash("Налаштування підписки збережено."); render(); }
  } catch (error) { flash(error.message, "error"); render(); }
});

root.addEventListener("change", async (event) => {
  if (event.target.matches("select[name='pharmacy']")) {
    try { await choosePharmacy(event.target.value); catalogFilters.pharmacy = String(event.target.value); catalogPageNumber = 1; render(); }
    catch (error) { flash(error.message, "error"); render(); }
  }
  if (event.target.matches("select[data-action='product-pharmacy']")) {
    try { await choosePharmacy(event.target.value); render(); }
    catch (error) { flash(error.message, "error"); render(); }
  }
  if (event.target.name === "fulfillment_method") { const group = document.querySelector(".recipient-fields"); group?.classList.toggle("hidden", event.target.value === "PICKUP"); for (const input of group?.querySelectorAll("input") || []) input.required = event.target.value !== "PICKUP"; }
  if (event.target.name === "payment_method") {
    const group = event.target.closest("form")?.querySelector("[data-cart-demo-card-fields]");
    const enabled = ["CARD", "ONLINE_GATEWAY"].includes(event.target.value) && Boolean(currentUser);
    group?.classList.toggle("hidden", !enabled);
    for (const input of group?.querySelectorAll("input,select") || []) {
      input.disabled = !enabled;
      input.required = enabled && input.name !== "demo_scenario";
      if (!enabled) input.value = "";
    }
    group?.querySelector("[data-cart-card-error]")?.classList.add("hidden");
  }
  if (event.target.name === "tier") {
    const form = event.target.closest("form");
    const social = form?.querySelector("[data-loyalty-social-fields]");
    const premium = form?.querySelector("[data-loyalty-premium-fields]");
    const isSocial = event.target.value === "SOCIAL";
    const isPremium = event.target.value === "PREMIUM";
    social?.classList.toggle("hidden", !isSocial);
    premium?.classList.toggle("hidden", !isPremium);
    const documentNumber = social?.querySelector("input[name='document_number']");
    if (documentNumber) { documentNumber.disabled = !isSocial; documentNumber.required = isSocial; if (!isSocial) documentNumber.value = ""; }
    for (const input of premium?.querySelectorAll("input,select") || []) {
      input.disabled = !isPremium;
      input.required = isPremium && input.name !== "demo_scenario";
      if (!isPremium) input.value = "";
    }
    premium?.querySelector("[data-loyalty-card-error]")?.classList.add("hidden");
  }
});

root.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-form]"); if (!form) return;
  event.preventDefault();
  const kind = form.dataset.form;
  const submitButton = form.querySelector('[type="submit"]');
  if (kind === "checkout") { await submitCartCheckout(form); return; }
  if (kind === "loyalty-tier") {
    const tier = form.elements.tier.value;
    const body = { tier };
    if (tier === "SOCIAL") body.document_number = form.elements.document_number.value;
    if (tier === "PREMIUM") {
      const credentials = {
        cardholder: form.elements.premium_cardholder?.value || "",
        card_number: form.elements.premium_card_number?.value || "",
        expiry: form.elements.premium_expiry?.value || "",
        cvv: form.elements.premium_cvv?.value || "",
      };
      const cardError = form.querySelector("[data-loyalty-card-error]");
      if (!isFictionalDemoCard(credentials)) {
        for (const name of ["premium_cardholder", "premium_card_number", "premium_expiry", "premium_cvv"]) if (form.elements[name]) form.elements[name].value = "";
        if (cardError) { cardError.textContent = "Введіть лише опубліковані тестові реквізити. Справжні картки не приймаються."; cardError.classList.remove("hidden"); }
        return;
      }
      const scenario = form.elements.demo_scenario.value;
      for (const name of ["premium_cardholder", "premium_card_number", "premium_expiry", "premium_cvv"]) form.elements[name].value = "";
      const keyStorage = `pharmacy.premiumPaymentKey.${currentUser.id}`;
      let key = sessionStorage.getItem(keyStorage);
      if (!key) { key = crypto.randomUUID(); sessionStorage.setItem(keyStorage, key); }
      Object.assign(body, { confirm_subscription: true, ...demoPaymentRequestPayload(key, scenario) });
      if (submitButton) { submitButton.disabled = true; submitButton.textContent = "Оплата обробляється…"; }
      try {
        const result = await api.request("/loyalty/", { method: "POST", body });
        sessionStorage.removeItem(keyStorage);
        flash(result.payment_status === "SUCCEEDED"
          ? "Симуляцію оплати схвалено. Підписка Premium активна 30 днів; кошти не списувалися."
          : result.payment_status === "FAILED"
            ? "Симуляцію оплати відхилено. Premium не активовано."
            : "Симуляція завершилася тайм-аутом. Підписку не активовано; спробуйте ще раз.", result.payment_status === "SUCCEEDED" ? "success" : "error");
        render();
      } catch (error) { flash(error.message, "error"); render(); }
      return;
    }
    if (submitButton) submitButton.disabled = true;
    try { await api.request("/loyalty/", { method: "POST", body }); flash("Програму лояльності оновлено."); render(); }
    catch (error) { flash(error.message, "error"); render(); }
    return;
  }
  if (submitButton && kind !== "demo-payment") submitButton.disabled = true;
  if (kind === "demo-payment") { await submitDemoPayment(form); return; }
  const formData = new FormData(form);
  const raw = Object.fromEntries(formData.entries());
  try {
    if (kind === "filters") { await choosePharmacy(raw.pharmacy); catalogFilters = { search: raw.search.trim(), category: raw.category, manufacturer: raw.manufacturer, pharmacy: raw.pharmacy || "" }; catalogPageNumber = 1; render(); }
    if (kind === "login") {
      const guestCart = await captureGuestCart();
      currentUser = await auth.signIn(raw.username, raw.password);
      const returnToCart = currentUser.role === "CUSTOMER" && Boolean(guestCart?.items.length);
      if (returnToCart) {
        try { const count = await mergeGuestCart(guestCart); flash(`Вхід успішний. Перенесено ${count} позицій гостьового кошика; кількості додано до збереженого кошика.`); }
        catch (error) { flash(`Ви увійшли, але кошик гостя перенесено не повністю. Товари гостя збережено для повторної спроби. ${error.message}`, "error"); }
      } else flash("Welcome back.");
      location.hash = returnToCart ? "cart" : "account";
      render();
    }
    if (kind === "register") {
      const guestCart = await captureGuestCart();
      currentUser = await auth.register(raw);
      const returnToCart = currentUser.role === "CUSTOMER" && Boolean(guestCart?.items.length);
      if (returnToCart) {
        try { const count = await mergeGuestCart(guestCart); flash(`Обліковий запис створено. Перенесено ${count} позицій гостьового кошика.`); }
        catch (error) { flash(`Обліковий запис створено, але кошик гостя перенесено не повністю. Товари гостя збережено для повторної спроби. ${error.message}`, "error"); }
      } else flash("Your customer account is ready.");
      location.hash = returnToCart ? "cart" : "account";
      render();
    }
    if (kind === "profile") { await api.request("/profile/", { method: "PATCH", body: { full_name: raw.full_name, phone: raw.phone || null, preferred_pharmacy_id: raw.preferred_pharmacy_id ? Number(raw.preferred_pharmacy_id) : null } }); flash("Profile saved."); render(); }
    if (kind === "preferences") { await api.request("/preferences/", { method: "POST", body: { promotions_enabled: form.elements.promotions_enabled.checked, reminders_enabled: form.elements.reminders_enabled.checked } }); flash("Preferences saved."); render(); }
    if (kind === "prescription") { await api.request("/prescriptions/", { method: "POST", body: { display_label: raw.display_label } }); flash("Prescription label saved."); render(); }
    if (kind === "reminder") { const nextRun = new Date(raw.next_run_at); if (nextRun <= new Date()) throw new Error("Дата нагадування має бути в майбутньому."); await api.request("/reminders/", { method: "POST", body: { product_id: Number(raw.product_id), interval_days: Number(raw.interval_days), next_run_at: nextRun.toISOString(), is_active: true } }); flash("Нагадування збережено через API."); render(); }
  } catch (error) { flash(error.message, "error"); render(); }
});

async function submitCartCheckout(form) {
  const submitButton = form.querySelector('[type="submit"]');
  const method = form.elements.payment_method?.value || "";
  const cardEnabled = ["CARD", "ONLINE_GATEWAY"].includes(method);
  let demoScenario = null;
  if (cardEnabled && currentUser) {
    const fields = form.querySelector("[data-cart-demo-card-fields]");
    const credentials = {
      cardholder: form.elements.demo_cardholder?.value || "",
      card_number: form.elements.demo_card_number?.value || "",
      expiry: form.elements.demo_expiry?.value || "",
      cvv: form.elements.demo_cvv?.value || "",
    };
    const error = fields?.querySelector("[data-cart-card-error]");
    if (!isFictionalDemoCard(credentials)) {
      if (error) { error.textContent = "Введіть лише опубліковані тестові реквізити. Дані реальної картки не приймаються."; error.classList.remove("hidden"); }
      for (const name of ["demo_cardholder", "demo_card_number", "demo_expiry", "demo_cvv"]) if (form.elements[name]) form.elements[name].value = "";
      return;
    }
    demoScenario = form.elements.demo_scenario?.value || "APPROVED";
    for (const name of ["demo_cardholder", "demo_card_number", "demo_expiry", "demo_cvv"]) if (form.elements[name]) form.elements[name].value = "";
  }
  const sensitiveNames = new Set(["demo_cardholder", "demo_card_number", "demo_expiry", "demo_cvv", "demo_scenario"]);
  const raw = Object.fromEntries([...form.elements]
    .filter((element) => element.name && !sensitiveNames.has(element.name) && !element.disabled && element.type !== "submit")
    .map((element) => [element.name, element.value]));
  if (submitButton) submitButton.disabled = true;
  try { await checkout(raw, demoScenario); }
  catch (error) { flash(error.message, "error"); render(); }
}

async function changeCart(productId, quantity, pharmacyId = "", refresh = true) {
  if (currentUser && currentUser.role !== "CUSTOMER") throw new Error("Кошик доступний лише гостям і клієнтам.");
  if (quantity > 0 && pharmacyId) await choosePharmacy(pharmacyId);
  const guest = !auth.token;
  await api.request(guest ? "/guest-cart/" : "/cart/", { method: "PUT", auth: !guest, body: { product_id: productId, quantity } });
  const branches = readCartBranches();
  if (quantity <= 0) delete branches[productId];
  else if (pharmacyId) branches[productId] = String(pharmacyId);
  writeCartBranches(branches);
  flash(quantity ? "Added to your bag." : "Removed from your bag.");
  if (refresh && page() === "cart") render(); else if (page() !== "cart") root.querySelector(".notice")?.remove();
}

function addOneToCart(productId, pharmacyId) {
  const operation = addToCartQueue.catch(() => {}).then(async () => {
    if (currentUser && currentUser.role !== "CUSTOMER") throw new Error("Кошик доступний лише гостям і клієнтам.");
    const branchId = String(pharmacyId || selectedPharmacyId || "");
    if (branchId) await choosePharmacy(branchId);
    const guest = !auth.token;
    const path = guest ? "/guest-cart/" : "/cart/";
    const cart = await api.request(path, { auth: !guest });
    const items = Array.isArray(cart.items)
      ? cart.items
      : Object.entries(cart.items || {}).map(([id, quantity]) => ({ product_id: Number(id), quantity }));
    const currentQuantity = Number(items.find((item) => Number(item.product_id) === productId)?.quantity || 0);
    const branches = readCartBranches();
    if (currentQuantity > 0 && branches[productId] && String(branches[productId]) !== branchId) {
      throw new Error("Цей товар уже додано з іншої аптеки. Видаліть його з кошика, щоб додати товар з цієї філії.");
    }
    await api.request(path, { method: "PUT", auth: !guest, body: { product_id: productId, quantity: currentQuantity + 1 } });
    branches[productId] = branchId;
    writeCartBranches(branches);
    flash(`Додано до кошика. Кількість: ${currentQuantity + 1}.`);
  });
  addToCartQueue = operation.catch(() => {});
  return operation;
}

async function checkout(raw, demoScenario = null) {
  if (!currentUser) { flash("Sign in to request a live quote and place an order.", "info"); location.hash = "login"; render(); return; }
  if (currentUser.role !== "CUSTOMER") throw new Error("Оформити замовлення може лише клієнтський обліковий запис.");
  const cart = await api.request("/cart/");
  const requestedIds = String(raw.product_ids || "").split(",").filter(Boolean).map(Number);
  const lines = (cart.items || []).filter((item) => requestedIds.includes(Number(item.product_id)));
  if (!lines.length) throw new Error("Your customer cart is empty. Add items and update your bag first.");
  if (lines.length !== new Set(requestedIds).size) throw new Error("Кошик змінився. Оновіть сторінку й перевірте товари цієї аптеки.");
  const quoteBody = { pharmacy_id: Number(raw.pharmacy_id), fulfillment_method: raw.fulfillment_method, items: lines, redeem_points: Number(raw.redeem_points || 0) };
  const quote = await api.request("/checkout/quote/", { method: "POST", body: quoteBody });
  const quoteItems = quote.lines || [];
  pendingOrder = {
    body: { ...quoteBody, payment_method: raw.payment_method, expected_total: quote.grand_total, items: quoteItems.map((item) => ({ product_id: item.product_id, quantity: item.quantity, expected_unit_price: item.price })), ...(raw.fulfillment_method !== "PICKUP" ? { recipient: { name: raw.recipient_name, phone: raw.recipient_phone, destination: raw.recipient_destination } } : {}) },
    quote,
    productIds: quoteItems.map((item) => Number(item.product_id)),
    ...(demoScenario ? { demoScenario } : {}),
  };
  const quoteRows = quoteItems.map((item) => `<tr><td>${e(item.name)}</td><td>${item.quantity}</td><td>${money(item.price)}</td><td>${money(Number(item.price) * item.quantity)}</td></tr>`);
  const content = `<section class="content narrow">${sectionHead("CHECKOUT", "Перевірте розрахунок аптеки", "Підсумкову суму розрахував сервер за актуальними цінами та залишками.")}${card(`${table(["ТОВАР", "КІЛЬКІСТЬ", "ЦІНА", "РАЗОМ"], quoteRows)}<dl class="quote-totals"><div><dt>Сума товарів</dt><dd>${money(quote.subtotal)}</dd></div><div><dt>Знижка програми/акції</dt><dd>− ${money(quote.discount)}</dd></div>${quote.points_redeemed ? `<div><dt>Оплата бонусами (${quote.points_redeemed})</dt><dd>− ${money(quote.bonus_discount)}</dd></div>` : ""}<div><dt>Доставка</dt><dd>${money(quote.shipping)}</dd></div><div class="quote-grand"><dt>Разом до сплати</dt><dd>${money(quote.grand_total)}</dd></div></dl><p class="fine-print">Спосіб оплати: ${e(raw.payment_method)} · Після підтвердження API повторно перевірить ціну та залишки.</p>${demoScenario ? `<p class="demo-payment-banner"><b>DEMO PAYMENT — NO REAL MONEY</b><br>Після підтвердження замовлення буде виконано обрану симуляцію карткової оплати.</p>` : ""}<div class="button-row"><button class="button secondary" data-action="back-to-cart">Повернутися до кошика</button><button class="button primary" data-action="confirm-order">${demoScenario ? "Підтвердити замовлення й оплатити" : "Підтвердити замовлення"}</button></div>`)}</section>`;
  root.innerHTML = localizeMarkup(shell(content));
}

async function confirmOrder() {
  if (!pendingOrder) throw new Error("Спочатку отримайте актуальний розрахунок замовлення.");
  const completedBatch = pendingOrder;
  const order = await api.request("/orders/", { method: "POST", body: completedBatch.body });
  const cleanup = await Promise.allSettled(completedBatch.productIds.map((productId) => api.request("/cart/", { method: "PUT", body: { product_id: productId, quantity: 0 } })));
  const branches = readCartBranches();
  for (const productId of completedBatch.productIds) delete branches[productId];
  writeCartBranches(branches);
  pendingOrder = null;
  const cleanupFailed = cleanup.some((result) => result.status === "rejected");
  if (completedBatch.demoScenario) {
    try {
      const keyStorage = `pharmacy.demoPaymentKey.${currentUser.id}.${order.id}`;
      let key = sessionStorage.getItem(keyStorage);
      if (!key) { key = crypto.randomUUID(); sessionStorage.setItem(keyStorage, key); }
      await api.request(`/orders/${encodeURIComponent(order.id)}/pay/`, { method: "POST", body: demoPaymentRequestPayload(key, completedBatch.demoScenario) });
      const result = await waitForDemoPaymentResult(order.id);
      flash(`Замовлення ${order.order_number || order.id}: ${demoPaymentMessage(result)}${cleanupFailed ? " Перевірте кошик: не всі позиції вдалося синхронізувати." : ""}`, result === "FAILED" ? "error" : "success");
    } catch (error) {
      flash(`Замовлення ${order.order_number || order.id} створено, але результат оплати не вдалося отримати: ${error.message}. Перевірте замовлення в історії.`, "error");
    }
    location.hash = "orders";
  } else {
    flash(`Замовлення ${order.order_number || order.id} оформлено${cleanupFailed ? ". Перевірте кошик: не всі позиції вдалося синхронізувати." : ". Інші аптечні замовлення залишилися в кошику."}`);
    location.hash = "cart";
  }
  render();
}

function demoPaymentMessage(result) {
  return ({ SUCCEEDED: "симуляцію оплати схвалено (це не авторизація банку)", FAILED: "симуляцію оплати відхилено", UNKNOWN: "статус оплати очікує уточнення після тайм-ауту" })[result] || "статус симульованої оплати очікує обробки";
}

async function waitForDemoPaymentResult(orderId) {
  const deadline = Date.now() + 5000;
  let result = "PENDING";
  while (Date.now() < deadline) {
    const fulfillment = await api.request(`/orders/${encodeURIComponent(orderId)}/fulfillment/`);
    const payments = fulfillment.payments || [];
    result = payments.slice().sort((a, b) => b.id - a.id)[0]?.status || result;
    if (["SUCCEEDED", "FAILED", "UNKNOWN"].includes(result)) return result;
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  return result;
}

render();
