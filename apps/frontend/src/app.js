import { api } from "./api.js";
import { auth } from "./auth.js";
import { button, card, empty, escapeHtml as e, field, listOf, money, sectionHead, selectField, table } from "./ui.js";

const root = document.querySelector("#app");
let currentUser = auth.user;
let busy = false;
let message = "";
let messageType = "success";
let catalogFilters = { search: "", category: "", manufacturer: "" };
let catalogPageNumber = 1;
let adminSections = [];
let pendingOrder = null;
const href = (route) => `#${route}`;

const translations = {
  "Loading…": "Завантаження…", "Loading pharmacy…": "Завантаження аптеки…", "Your session expired. Please sign in again.": "Сесію завершено. Увійдіть знову.",
  "Sign in": "Увійти", "Sign out": "Вийти", "Create an account": "Створити обліковий запис", "Create account": "Створити обліковий запис", "My account": "Мій кабінет",
  "Shop": "Каталог", "Locations": "Аптеки", "Administration": "Адміністрування", "Staff": "Персонал", "Bag": "Кошик", "Your bag": "Кошик", "YOUR BAG": "ВАШ КОШИК",
  "GOOD CARE, CLOSE BY": "ТУРБОТА ПОРУЧ", "A little better,": "Турбота щодня,", "every day.": "для вашого здоров’я.",
  "Thoughtful essentials and trusted pharmacy care, ready when you need them.": "Необхідні товари та турбота аптеки — поруч, коли вони потрібні.", "Explore products": "Переглянути товари", "Local pharmacy network": "Мережа аптек", "Simple ordering": "Зручне замовлення",
  "THE EVERYDAY EDIT": "КАТАЛОГ АПТЕКИ", "Find what feels good": "Оберіть потрібне", "Browse our live pharmacy catalog.": "Каталог товарів, завантажений з API аптеки.", "products": "товарів", "Search product or SKU": "Пошук за назвою або SKU", "Search": "Пошук", "All categories": "Усі категорії", "All manufacturers": "Усі виробники", "Apply filters": "Застосувати фільтри", "No products found": "Товарів не знайдено", "Try another search or remove a filter.": "Змініть пошук або приберіть фільтр.", "Live price at checkout": "Ціну підтвердить аптека", "Add": "Додати", "EVERYDAY CARE": "ЩОДЕННИЙ ДОГЛЯД", "PRESCRIPTION": "РЕЦЕПТУРНИЙ", "Page": "Сторінка", "Showing": "Показано", "Previous": "Назад", "Next page": "Наступна сторінка", "Carefully sourced": "Перевірені товари", "A pharmacy near you": "Аптека поруч", "Here for your wellbeing": "Турбота про здоров’я",
  "PRODUCT DETAILS": "ІНФОРМАЦІЯ ПРО ТОВАР", "Back to shop": "Назад до каталогу", "PRESCRIPTION REQUIRED": "ПОТРІБЕН РЕЦЕПТ", "PHARMACY ESSENTIAL": "АПТЕЧНИЙ ТОВАР", "Available at": "Наявність в аптеках", "No availability listed": "Немає даних про наявність", "Check with a local pharmacy for current stock.": "Уточніть залишки у вибраній аптеці.", "Watch availability": "Стежити за наявністю", "Add to bag": "До кошика", "Find a pharmacy": "Знайти аптеку", "HERE FOR YOU": "МИ ПОРУЧ", "View listed stock": "Переглянути залишки", "No locations available": "Аптек не знайдено", "Please check back later.": "Спробуйте пізніше.",
  "A good choice.": "Вдалий вибір.", "Your pharmacy confirms the final price and stock before your order is placed.": "Аптека підтвердить ціну та наявність перед замовленням.", "Choose your pharmacy": "Оберіть аптеку", "Pharmacy": "Аптека", "Fulfillment": "Спосіб отримання", "Payment": "Оплата", "Pickup": "Самовивіз", "Courier delivery": "Кур’єрська доставка", "Postal delivery": "Поштова доставка", "Recipient name": "Ім’я отримувача", "Phone": "Телефон", "Destination": "Адреса доставки", "Request quote": "Розрахувати замовлення", "Your bag is waiting": "Кошик порожній", "Add something you need and it will appear here.": "Додайте товари з каталогу.", "Update quantities": "Оновити кількість", "Continue shopping": "Продовжити покупки", "Remove": "Видалити", "CHECKOUT": "ОФОРМЛЕННЯ", "Payments are simulated. No card details are collected here.": "Оплата навчальна та імітована. Дані банківських карток не запитуються.",
  "WELCOME BACK": "ВІТАЄМО", "Your account": "Ваш обліковий запис", "Account type:": "Тип облікового запису:", "Continue to your dashboard": "Перейти до кабінету", "GOODWELL PHARMACY": "ІНТЕРНЕТ-АПТЕКА", "Care starts<br>with a <em>hello.</em>": "Турбота починається<br>зі <em>знайомства.</em>", "Sign in to manage your orders and make everyday care a little simpler.": "Увійдіть, щоб керувати замовленнями та профілем.", "YOUR ACCOUNT": "МІЙ КАБІНЕТ", "Welcome back": "З поверненням", "Sign in with your pharmacy account.": "Введіть дані облікового запису.", "Username": "Ім’я користувача", "Password": "Пароль", "New to Goodwell?": "Ще не маєте облікового запису?", "JOIN GOODWELL": "РЕЄСТРАЦІЯ", "Start with the essentials.": "Заповніть основні дані.", "Full name": "Повне ім’я", "Create my account": "Створити обліковий запис", "Already have an account?": "Вже зареєстровані?",
  "PROFILE": "ПРОФІЛЬ", "Your details": "Ваші дані", "Preferred pharmacy": "Бажана аптека", "Save details": "Зберегти дані", "YOUR CARE": "ВАШІ ДАНІ", "Saved prescriptions": "Збережені рецептурні позначки", "Nothing saved": "Немає збережених записів", "Add a demo label to help identify your prescription record.": "Додайте назву для позначення запису рецепта.", "Display label": "Назва позначки", "Add label": "Додати позначку", "This demo stores a masked reference only, not a prescription image or medical document.": "Зберігається лише замасковане посилання, без зображення чи медичного документа.", "LOYALTY": "ЛОЯЛЬНІСТЬ", "member": "учасник програми", "points": "балів", "View orders": "Переглянути замовлення", "PREFERENCES": "НАЛАШТУВАННЯ", "Keep in touch": "Сповіщення", "Pharmacy offers": "Пропозиції аптеки", "Order reminders": "Нагадування про замовлення", "Save preferences": "Зберегти налаштування", "NOTIFICATIONS": "СПОВІЩЕННЯ", "Recent updates": "Останні оновлення", "All caught up": "Нових сповіщень немає", "New account notifications will appear here.": "Тут відображатимуться нові сповіщення.", "Mark read": "Позначити прочитаним", "Overview": "Огляд", "Orders": "Замовлення", "No orders yet": "Замовлень поки немає", "Track an order, pay for a simulated purchase or request a reorder.": "Переглядайте замовлення, імітовану оплату та повторне замовлення.", "Order history": "Історія замовлень", "Pay now": "Оплатити (імітація)", "Cancel order": "Скасувати замовлення", "Reorder": "Замовити знову", "Fulfillment": "Доставка",
  "PHARMACY TEAM": "РОБОТА АПТЕКИ", "Branch workspace": "Робоче місце аптеки", "Inventory updates and order actions are checked by the API for your assigned branch.": "API перевіряє доступ до призначеної аптеки.", "Assigned pharmacy": "Призначена аптека", "Completed order total": "Сума виконаних замовлень", "Order states": "Стани замовлень", "STOCK CONTROL": "ОБЛІК ЗАПАСІВ", "Inventory": "Залишки", "PRODUCT": "ТОВАР", "AVAILABLE": "ДОСТУПНО", "PRICE": "ЦІНА", "ADJUST": "ЗМІНА", "Save": "Зберегти", "ORDER DESK": "ЗАМОВЛЕННЯ", "Branch orders": "Замовлення аптеки", "No branch orders": "Замовлень немає", "New orders for this pharmacy appear here.": "Тут з’являтимуться замовлення аптеки.", "AUDIT": "ЖУРНАЛ ДІЙ", "Recent branch activity": "Останні дії", "Load activity": "Завантажити журнал", "No assigned pharmacy": "Аптеку не призначено", "Ask a network administrator to assign an active pharmacy to your account.": "Зверніться до адміністратора для призначення аптеки.",
  "NETWORK ADMINISTRATION": "АДМІНІСТРУВАННЯ МЕРЕЖІ", "Network overview": "Огляд мережі", "All privileged changes are sent to the API and checked against your ADMIN role.": "API перевіряє права адміністратора для кожної зміни.", "COMPLETED ORDER TOTAL": "СУМА ВИКОНАНИХ ЗАМОВЛЕНЬ", "ORDER STATUSES": "СТАНИ ЗАМОВЛЕНЬ", "ACCESS": "ДОСТУП", "Administrator": "Адміністратор", "Users": "Користувачі", "Pharmacies": "Аптеки", "Products": "Товари", "Categories": "Категорії", "Manufacturers": "Виробники", "Assignments": "Призначення персоналу", "Promotions": "Акції", "Loyalty tiers": "Рівні лояльності", "Delivery rules": "Правила доставки", "Promotion products": "Товари акцій", "Edit": "Редагувати", "New record": "Новий запис", "No records": "Записів немає", "Create the first record with the form below.": "Створіть перший запис за допомогою форми.", "Create": "Створити", "records": "записів", "Retry": "Повторити", "This page could not load": "Не вдалося завантажити сторінку", "Try again once the API is available.": "Перевірте API та спробуйте ще раз.", "WE HIT A SNAG": "СТАЛАСЯ ПОМИЛКА", "This area is for customers": "Цей розділ доступний клієнтам", "Sign in to continue": "Увійдіть, щоб продовжити", "Manage orders, profile details and loyalty information.": "Керуйте замовленнями, профілем і бонусами.", "Delete": "Видалити", "Submit": "Підтвердити", "Confirm order": "Підтвердити замовлення", "Review server quote": "Перевірте розрахунок аптеки", "Server total": "Сума за розрахунком аптеки", "Subtotal": "Сума товарів", "Discount": "Знижка", "Delivery": "Доставка", "Back to cart": "Повернутися до кошика", "Paid": "Оплачено", "Pending": "Очікує", "Payment status": "Стан оплати", "Status": "Стан", "Product": "Товар", "Quantity": "Кількість", "Unit price": "Ціна за одиницю", "There are no records to show.": "Немає записів для відображення.", "API response": "Відповідь API", "Cancel": "Скасувати", "Close": "Закрити", "Create promotion-product link": "Прив’язати товар до акції", "Goodwell pharmacy network": "МЕРЕЖА АПТЕК GOODWELL", "care that fits your day": "турбота щодня", "Our pharmacies": "Наші аптеки", "Customer care": "Підтримка клієнтів", "Educational demo · simulated services": "Навчальний проєкт · імітовані сервіси", "Toggle navigation": "Відкрити меню", "Everyday care": "Щоденний догляд", "No preference": "Без побажань", "Item": "Товар", "Quantity": "Кількість", "Active": "Активний", "Hidden": "Прихований", "Listed": "У продажу", "Order desk": "Замовлення", "Password (12+ characters)": "Пароль (не менше 12 символів)", "Email": "Електронна пошта", "Role": "Роль", "Code": "Код", "Address": "Адреса", "City": "Місто", "Phone": "Телефон", "Description": "Опис", "Category": "Категорія", "Manufacturer": "Виробник", "Prescription required": "Потрібен рецепт", "Storage minimum °C": "Мінімальна температура зберігання, °C", "Storage maximum °C": "Максимальна температура зберігання, °C", "Discount rate": "Розмір знижки", "Bonus rate": "Бонусна ставка", "Starts at": "Початок дії", "Ends at": "Кінець дії", "Method": "Спосіб", "Enabled": "Увімкнено", "Requires cold chain": "Потрібен холодовий ланцюг", "Cold chain supported": "Холодовий ланцюг доступний", "Promotion ID": "ID акції", "Product ID": "ID товару", "User ID": "ID користувача", "Staff user ID": "ID працівника", "Pharmacy ID": "ID аптеки", "Code": "Код", "TOGGLE": "Змінити", "Create user": "Створити користувача", "Create pharmacy": "Створити аптеку", "Create product": "Створити товар", "Create category": "Створити категорію", "Create manufacturer": "Створити виробника", "Create assignments": "Створити призначення персоналу", "Create promotions": "Створити акцію", "Create loyalty tiers": "Створити рівень лояльності", "Create delivery rules": "Створити правило доставки", "Create promotion products": "Прив’язати товар до акції"
};
function localizeMarkup(markup) {
  const template = document.createElement("template");
  template.innerHTML = markup;
  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const leading = node.textContent.match(/^\s*/)?.[0] || "";
    const trailing = node.textContent.match(/\s*$/)?.[0] || "";
    const key = node.textContent.trim();
    if (translations[key]) node.textContent = `${leading}${translations[key]}${trailing}`;
  }
  for (const element of template.content.querySelectorAll("*")) {
    for (const attribute of ["placeholder", "aria-label", "title"]) {
      const value = element.getAttribute(attribute);
      if (value && translations[value]) element.setAttribute(attribute, translations[value]);
    }
  }
  return template.innerHTML;
}
const orderStatus = (status) => ({ PENDING_PAYMENT: "Очікує оплати", CONFIRMED: "Підтверджено", PROCESSING: "В обробці", READY_FOR_PICKUP: "Готове до самовивозу", AWAITING_SHIPMENT: "Очікує відправлення", SHIPPED: "Відправлено", COMPLETED: "Виконано", CANCELLED: "Скасовано" })[status] || status;
const paymentMethod = (method) => ({ CARD: "Картка (імітація)", BANK_TRANSFER: "Банківський переказ (імітація)", CASH_ON_DELIVERY: "Оплата при отриманні (імітація)", ONLINE_GATEWAY: "Онлайн-шлюз (імітація)" })[method] || method;
const adminLabels = { Users: "Користувачі", Pharmacies: "Аптеки", Products: "Товари", Categories: "Категорії", Manufacturers: "Виробники", Assignments: "Призначення персоналу", Promotions: "Акції", "Promotion products": "Товари акцій", "Loyalty tiers": "Рівні лояльності", "Delivery rules": "Правила доставки" };
const createLabels = { Users: "Створити користувача", Pharmacies: "Створити аптеку", Products: "Створити товар", Categories: "Створити категорію", Manufacturers: "Створити виробника", Assignments: "Створити призначення", Promotions: "Створити акцію", "Promotion products": "Прив’язати товар до акції", "Loyalty tiers": "Створити рівень лояльності", "Delivery rules": "Створити правило доставки" };

window.addEventListener("hashchange", render);
window.addEventListener("auth-expired", () => { auth.clear(); currentUser = null; flash("Сесію завершено. Увійдіть знову.", "error"); render(); });
window.addEventListener("DOMContentLoaded", () => {});

function flash(text, type = "success") { message = text; messageType = type; }
function page() { return (location.hash.replace(/^#/, "").split("?")[0]) || "home"; }
function navLink(name, route, active) { return `<a class="nav-link ${active ? "active" : ""}" href="${href(route)}">${name}</a>`; }
function addCartControl(productId, productName, style = "round-action") {
  if (currentUser && currentUser.role !== "CUSTOMER") return `<span class="muted" aria-label="Покупки доступні клієнтам">Кошик для клієнтів</span>`;
  return `<button class="${style}" data-action="add" data-id="${productId}" aria-label="Додати до кошика: ${e(productName)}">${style === "round-action" ? "＋" : "До кошика"}</button>`;
}
function shell(content) {
  const route = page().split(":")[0];
  const user = currentUser;
  const roleLink = user?.role === "STAFF" ? navLink("Staff", "staff", route === "staff") : user?.role === "ADMIN" ? navLink("Administration", "admin", route === "admin") : "";
  return `<header class="topbar"><a class="brand" href="#home"><span class="brand-icon">+</span><span>goodwell<span class="brand-sub">МЕРЕЖА АПТЕК</span></span></a><nav class="main-nav">${navLink("Shop", "home", ["home", "product"].includes(route))}${navLink("Locations", "pharmacies", route === "pharmacies")}${user?.role === "CUSTOMER" ? navLink("My account", "account", route === "account" || route === "orders") : ""}${roleLink}</nav><div class="nav-actions">${user ? `<span class="user-chip">${e(user.username)} <small>${e(user.role)}</small></span><button class="text-button" data-action="logout">Sign out</button>` : navLink("Sign in", "login", route === "login")}${navLink("Bag", "cart", route === "cart")}<span class="bag-dot">+</span></div><button class="menu-toggle" data-action="menu" aria-label="Відкрити меню">☰</button></header><main>${message ? `<div class="notice ${messageType}" role="status">${e(message)}<button data-action="dismiss" aria-label="Закрити повідомлення">×</button></div>` : ""}${busy ? `<div class="loading-bar"><span></span></div>` : ""}${content}</main><footer><div class="footer-brand">goodwell<span>турбота щодня</span></div><div class="footer-links"><a href="#pharmacies">Наші аптеки</a><a href="#account">Підтримка клієнтів</a><span>Навчальний проєкт · імітовані сервіси</span></div></footer>`;
}

async function render() {
  const route = page();
  busy = true;
  root.innerHTML = shell(`<div class="page-loading">Loading…</div>`);
  try {
    if (auth.token && !currentUser) currentUser = await auth.loadUser();
    let content;
    if (route === "home") content = await catalogPage();
    else if (route === "catalog") content = await catalogPage();
    else if (route.startsWith("product:")) content = await productPage(route.split(":")[1]);
    else if (route === "pharmacies") content = await pharmaciesPage();
    else if (route === "cart") content = await cartPage();
    else if (route === "login" || route === "register") content = authPage(route);
    else if (route === "account") content = await accountPage();
    else if (route === "orders") content = await ordersPage();
    else if (route === "staff") content = await staffPage();
    else if (route === "admin") content = await adminPage();
    else content = notFoundPage();
    busy = false;
    root.innerHTML = localizeMarkup(shell(content));
  } catch (error) {
    busy = false;
    root.innerHTML = localizeMarkup(shell(`<section class="content narrow">${sectionHead("WE HIT A SNAG", "This page could not load")}${card(`<div class="error-panel"><strong>${e(error.message)}</strong><p>Try again once the API is available.</p>${button("Retry", "retry", "secondary")}</div>`)}</section>`));
  }
}

function notFoundPage() {
  return `<section class="content narrow">${sectionHead("404", "Сторінку не знайдено", "Перевірте адресу або поверніться до каталогу.")}${card(`<a class="button primary" href="#home">До каталогу</a>`)}</section>`;
}

async function catalogPage() {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(catalogFilters)) if (value) query.set(key, value);
  if (catalogPageNumber > 1) query.set("page", String(catalogPageNumber));
  const [productData, categoryData, manufacturerData, pharmacyData] = await Promise.all([
    api.request(`/products/${query.size ? `?${query}` : ""}`, { auth: currentUser?.role === "ADMIN" }),
    api.request("/categories/", { auth: false }), api.request("/manufacturers/", { auth: false }), api.request("/pharmacies/", { auth: false }),
  ]);
  const products = listOf(productData), categories = listOf(categoryData), manufacturers = listOf(manufacturerData), pharmacies = listOf(pharmacyData);
  const byId = (items, id) => items.find((item) => item.id === id)?.name || "—";
  return `<section class="hero"><div class="hero-copy"><p class="eyebrow">ТУРБОТА ПОРУЧ</p><h1>Турбота щодня,<br><em>для вашого здоров’я.</em></h1><p>Необхідні товари та турбота аптеки — поруч, коли вони потрібні.</p><a class="button primary" href="#catalog">Переглянути товари <span>↗</span></a><div class="hero-proof"><span>●</span> Мережа аптек <b>·</b> Зручне замовлення</div></div><div class="hero-art" aria-label="Ілюстрація рослини"><div class="sun"></div><div class="leaf leaf-one"></div><div class="leaf leaf-two"></div><div class="plant-stem"></div><div class="jar"><span>g</span></div><div class="art-label">турбота<br>щодня</div></div></section><section class="content" id="catalog"><div class="section-head"><div><p class="eyebrow">КАТАЛОГ АПТЕКИ</p><h2>Оберіть потрібне</h2><p class="muted">Каталог товарів, завантажений з API аптеки.</p></div><div class="result-note">${productData.count ?? products.length} товарів</div></div><form class="filterbar" data-form="filters"><label class="search-field"><span>⌕</span><input name="search" value="${e(catalogFilters.search)}" placeholder="Пошук за назвою або SKU" aria-label="Пошук"></label><select name="category"><option value="">Усі категорії</option>${categories.map((x) => `<option value="${x.id}" ${String(catalogFilters.category) === String(x.id) ? "selected" : ""}>${e(x.name)}</option>`).join("")}</select><select name="manufacturer"><option value="">Усі виробники</option>${manufacturers.map((x) => `<option value="${x.id}" ${String(catalogFilters.manufacturer) === String(x.id) ? "selected" : ""}>${e(x.name)}</option>`).join("")}</select><button class="button secondary" type="submit">Застосувати фільтри</button></form><div class="product-grid">${products.length ? products.map((p, i) => `<article class="product-card"><a class="product-image tone-${i % 4}" href="#product:${p.id}"><span class="product-number">${String(i + 1).padStart(2, "0")}</span><span class="bottle"></span><span class="product-tag">${p.prescription_required ? "ПОТРІБЕН РЕЦЕПТ" : "ЩОДЕННИЙ ДОГЛЯД"}</span></a><div class="product-info"><p class="product-meta">${e(byId(categories, p.category))} · ${e(byId(manufacturers, p.manufacturer))}</p><h3><a href="#product:${p.id}">${e(p.name)}</a></h3><p class="product-description">${e(p.description || "Фармацевтичні товари для повсякденних потреб.")}</p><div class="product-foot"><span class="muted">Ціну підтвердить аптека</span>${addCartControl(p.id, p.name)}</div></div></article>`).join("") : empty("Товарів не знайдено", "Змініть пошук або приберіть фільтр.")}</div><div class="catalog-foot"><span>Сторінка ${catalogPageNumber} · показано ${products.length} із ${productData.count ?? products.length}</span><span>${catalogPageNumber > 1 ? `<button class="text-button" data-action="previous-page">← Назад</button>` : ""}${productData.next ? `<button class="text-button" data-action="next-page">Наступна сторінка →</button>` : ""}</span></div></section><section class="service-strip"><span>✳ Перевірені товари</span><span>⌂ Аптека поруч</span><span>♡ Турбота про здоров’я</span></section>`;
}

async function productPage(id) {
  const p = await api.request(`/products/${encodeURIComponent(id)}/`, { auth: false });
  const [availableResult, categories, manufacturers] = await Promise.allSettled([api.request(`/products/${p.id}/availability/`, { auth: false }), api.request("/categories/", { auth: false }), api.request("/manufacturers/", { auth: false })]);
  if (categories.status === "rejected" || manufacturers.status === "rejected") throw (categories.reason || manufacturers.reason);
  const availabilityError = availableResult.status === "rejected" ? availableResult.reason : null;
  const available = availableResult.status === "fulfilled" ? availableResult.value : [];
  return `<section class="content product-detail"><a class="back-link" href="#home">← Назад до каталогу</a><div class="detail-grid"><div class="detail-art tone-1"><span class="bottle large"></span><span class="product-tag">${p.prescription_required ? "ПОТРІБЕН РЕЦЕПТ" : "АПТЕЧНИЙ ТОВАР"}</span></div><div>${sectionHead("ІНФОРМАЦІЯ ПРО ТОВАР", e(p.name))}<p class="lead">${e(p.description || "Фармацевтичні товари для повсякденних потреб.")}</p><p class="muted">${e(listOf(categories.value).find((x) => x.id === p.category)?.name || "")} · ${e(listOf(manufacturers.value).find((x) => x.id === p.manufacturer)?.name || "")}</p><p class="muted">Артикул: ${e(p.sku)}</p>${p.storage_min_c !== null || p.storage_max_c !== null ? `<p class="muted">Умови зберігання з каталогу: ${e(p.storage_min_c ?? "—")}°C – ${e(p.storage_max_c ?? "—")}°C</p>` : ""}${p.prescription_required ? `<div class="notice info inline">Для цього товару потрібен рецепт. Наявність і правила оформлення перевірить API аптеки.</div>` : ""}<h3>Наявність в аптеках</h3><div class="availability-list">${availabilityError ? `<div class="notice error inline">${e(availabilityError.message)}</div>` : listOf(available).length ? listOf(available).map((a) => `<div><span><b>${e(a.pharmacy__name)}</b><small>доступно: ${a.available}</small></span><strong>${money(a.unit_price)}</strong>${addCartControl(p.id, p.name, "button secondary small")}</div>`).join("") : empty("Немає даних про наявність", "Уточніть залишки у вибраній аптеці.")}</div>${currentUser?.role === "CUSTOMER" ? `<label class="field"><span>Аптека для сповіщення</span><select id="watch-pharmacy">${listOf(available).map((a) => `<option value="${a.pharmacy_id}">${e(a.pharmacy__name)}</option>`).join("")}</select></label>${button("Стежити за наявністю", "watch-product", "secondary", `data-id="${p.id}"`)}` : `<p class="fine-print">Щоб стежити за наявністю, увійдіть як клієнт.</p>`}<p class="fine-print">Ціну й залишок підтверджує аптека для конкретного замовлення.</p></div></div></section>`;
}

async function pharmaciesPage() {
  const data = await api.request("/pharmacies/", { auth: false });
  return `<section class="content">${sectionHead("МИ ПОРУЧ", "Знайти аптеку", "Перелік філій, які повернув API аптеки.")}<div class="location-grid">${listOf(data).map((p, i) => `<article class="location-card"><div class="location-art art-${i % 3}"><span>⌂</span><small>${e(p.city)}</small></div><div class="location-body"><p class="eyebrow">${e(p.code)}</p><h2>${e(p.name)}</h2><p>${e(p.address)}, ${e(p.city)}</p><p>${e(p.phone || "Контакти можна уточнити у філії")}</p><button class="button secondary" data-action="inventory" data-id="${p.id}">Переглянути залишки</button><div class="stock-preview" id="stock-${p.id}"></div></div></article>`).join("") || empty("Аптек не знайдено", "Перевірте пізніше.")}</div></section>`;
}

async function cartPage() {
  if (currentUser && currentUser.role !== "CUSTOMER") return `<section class="content narrow">${sectionHead("YOUR BAG", "Кошик клієнта", "Кошик доступний лише гостьовому або клієнтському сеансу.")}${card(`<p>Вийдіть з облікового запису або увійдіть як клієнт, щоб працювати з кошиком.</p><button class="button secondary" data-action="logout">Вийти</button>`)}</section>`;
  const guest = !auth.token;
  const cart = await api.request(guest ? "/guest-cart/" : "/cart/", { auth: !guest });
  let items = cart.items || [];
  if (!Array.isArray(items)) items = Object.entries(items).map(([product_id, quantity]) => ({ product_id: Number(product_id), quantity }));
  const [productsData, pharmaciesData, payments] = await Promise.all([api.request("/products/", { auth: currentUser?.role === "ADMIN" }), api.request("/pharmacies/", { auth: false }), api.request("/payment-methods/", { auth: false })]);
  const products = listOf(productsData), pharmacies = listOf(pharmaciesData);
  const rows = items.map((i) => { const p = products.find((x) => x.id === i.product_id); return p ? `<tr><td><b>${e(p.name)}</b><small>${e(p.sku)}</small></td><td><input class="quantity-input" type="number" min="0" max="10000" value="${i.quantity}" data-quantity="${p.id}" aria-label="Кількість: ${e(p.name)}"></td><td><button class="text-button danger-text" data-action="remove" data-id="${p.id}">Видалити</button></td></tr>` : ""; });
  return `<section class="content">${sectionHead("ВАШ КОШИК", "Вдалий вибір.", "Аптека підтвердить актуальну ціну та наявність перед оформленням.")}<div class="cart-layout"><div>${card(items.length ? `${table(["ТОВАР", "КІЛЬКІСТЬ", ""], rows)}<div class="cart-actions"><button class="button secondary" data-action="update-cart">Оновити кількість</button><a class="text-button" href="#home">Продовжити покупки →</a></div>` : empty("Кошик порожній", "Додайте товари з каталогу."))}<p class="fine-print">${guest ? "Гостьовий кошик зберігається API в cookie браузера." : "Кошик пов’язаний з обліковим записом клієнта."}</p></div><aside class="checkout-card"><p class="eyebrow">ОФОРМЛЕННЯ</p><h2>Оберіть аптеку</h2>${items.length ? `<form data-form="checkout">${selectField("Аптека", "pharmacy_id", pharmacies.map((p) => [p.id, `${p.name} — ${p.city}`]), true)}${selectField("Спосіб отримання", "fulfillment_method", [["PICKUP", "Самовивіз"], ["COURIER", "Кур’єрська доставка"], ["POSTAL", "Поштова доставка"]], true)}${selectField("Оплата", "payment_method", (payments.methods || []).map((x) => [x, paymentMethod(x)]), true)}<div class="form-group recipient-fields hidden">${field("Ім’я отримувача", "recipient_name", "text", false)}${field("Телефон отримувача", "recipient_phone", "tel", false)}${field("Адреса доставки", "recipient_destination", "text", false)}</div><button class="button primary full" type="submit">${guest ? "Увійдіть, щоб оформити" : "Розрахувати замовлення"} <span>→</span></button></form>` : `<a class="button primary full" href="#home">До каталогу</a>`}<p class="fine-print">Оплата імітована. Дані карток не запитуються.</p></aside></div></section>`;
}

function authPage(route) {
  if (currentUser) return `<section class="content narrow">${sectionHead("ВІТАЄМО", `Ви увійшли як ${e(currentUser.username)}`)}${card(`<p>Тип облікового запису: <b>${e(({ CUSTOMER: "Клієнт", STAFF: "Працівник аптеки", ADMIN: "Адміністратор" })[currentUser.role] || currentUser.role)}</b></p><a class="button primary" href="#${currentUser.role === "ADMIN" ? "admin" : currentUser.role === "STAFF" ? "staff" : "account"}">Перейти до кабінету</a>`)}</section>`;
  return `<section class="auth-layout"><div class="auth-visual"><p class="eyebrow">ІНТЕРНЕТ-АПТЕКА GOODWELL</p><h1>Турбота починається<br>зі <em>знайомства.</em></h1><p>Увійдіть, щоб керувати профілем і замовленнями.</p></div><div class="auth-form-wrap">${route === "login" ? `<p class="eyebrow">ОБЛІКОВИЙ ЗАПИС</p><h1>З поверненням</h1><p class="muted">Введіть ім’я користувача та пароль.</p><form data-form="login">${field("Ім’я користувача", "username", "text", true)}${field("Пароль", "password", "password", true)}<button class="button primary full" type="submit">Увійти <span>→</span></button></form><p class="switch-auth">Ще не зареєстровані? <a href="#register">Створити обліковий запис</a></p>` : `<p class="eyebrow">РЕЄСТРАЦІЯ</p><h1>Створити обліковий запис</h1><p class="muted">Новий обліковий запис буде клієнтським.</p><form data-form="register">${field("Повне ім’я", "full_name", "text", true)}${field("Електронна пошта", "email", "email", true)}${field("Ім’я користувача", "username", "text", true)}<label class="field"><span>Пароль (не менше 12 символів)</span><input name="password" type="password" minlength="12" maxlength="128" required autocomplete="new-password"></label><button class="button primary full" type="submit">Зареєструватися <span>→</span></button></form><p class="switch-auth">Вже маєте обліковий запис? <a href="#login">Увійти</a></p>`}</div></section>`;
}

async function accountPage() {
  if (!currentUser) return signedOut();
  if (currentUser.role !== "CUSTOMER") return `<section class="content narrow">${sectionHead("ACCOUNT", "This area is for customers")}</section>`;
  const responses = await Promise.allSettled([
    api.request("/profile/"), api.request("/preferences/"), api.request("/loyalty/"), api.request("/notifications/"), api.request("/reminders/"), api.request("/availability-watches/"), api.request("/prescriptions/"),
    api.request("/pharmacies/", { auth: false }), api.request("/orders/"), api.request("/products/", { auth: false }),
  ]);
  const names = ["Profile", "notification preferences", "loyalty", "notifications", "reminders", "availability watches", "saved prescriptions", "pharmacies", "orders", "products"];
  const loadFailures = responses.flatMap((result, index) => result.status === "rejected" ? [`${names[index]}: ${result.reason.message}`] : []);
  const [profile, preferences, loyalty, notifications, reminders, watches, prescriptions, pharmaciesData, orders, productData] = responses.map((result) => result.status === "fulfilled" ? result.value : {});
  const prefs = listOf(preferences)[0] || {};
  const pharmacyOptions = [["", "No preference"], ...listOf(pharmaciesData).map((p) => [p.id, p.name])];
  const profileCard = card(`<p class="eyebrow">PROFILE</p><h2>Your details</h2><form data-form="profile">${field("Full name", "full_name", "text", true, profile.full_name)}${field("Phone", "phone", "tel", false, profile.phone || "")}${selectField("Preferred pharmacy", "preferred_pharmacy_id", pharmacyOptions)}<button class="button secondary" type="submit">Save details</button></form>`);
  const prescriptionsTable = listOf(prescriptions).length
    ? table(["LABEL", "REFERENCE", ""], listOf(prescriptions).map((x) => `<tr><td>${e(x.display_label)}</td><td>${e(x.masked_reference)}</td><td><button class="text-button danger-text" data-action="delete-prescription" data-id="${x.id}">Remove</button></td></tr>`))
    : empty("Nothing saved", "Add a demo label to help identify your prescription record.");
  const careCard = card(`<p class="eyebrow">YOUR CARE</p><h2>Saved prescriptions</h2>${prescriptionsTable}<form class="inline-form" data-form="prescription">${field("Display label", "display_label", "text", true)}<button class="button secondary" type="submit">Add label</button></form><p class="fine-print">This demo stores a masked reference only, not a prescription image or medical document.</p>`);
  const loyaltyCard = card(`<p class="eyebrow">LOYALTY</p><h2>${e(loyalty.account?.tier__code || "STANDARD")} member</h2><p class="points">${e(loyalty.account?.balance ?? 0)} <small>points</small></p>${listOf(loyalty.transactions).length ? `<details><summary>Останні операції бонусного рахунку</summary><ul>${listOf(loyalty.transactions).slice(0, 5).map((x) => `<li>${e(x.type || x.transaction_type || "Операція")}: ${e(x.points ?? x.amount ?? "—")}</li>`).join("")}</ul></details>` : ""}<a href="#orders" class="text-button">View orders →</a>`);
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
  if (currentUser.role !== "CUSTOMER") return `<section class="content narrow">${sectionHead("ЗАМОВЛЕННЯ", "Перегляд доступний клієнтам")}${card(`<p>Для роботи із замовленнями аптеки відкрийте робочий кабінет.</p><a class="button primary" href="#staff">До робочого кабінету</a>`)}</section>`;
  const data = await api.request("/orders/");
  const orders = listOf(data);
  const traces = await Promise.all(orders.map((o) => api.request(`/orders/${o.id}/fulfillment/`).catch((error) => ({ error: error.message }))));
  return `<section class="content">${sectionHead("МІЙ КАБІНЕТ", "Історія замовлень", "Перегляд замовлень, стану оплати та доставки.")}<div class="account-tabs">${navLink("Огляд", "account", false)}${navLink("Замовлення", "orders", true)}${navLink("Кошик", "cart", false)}</div>${orders.length ? `<div class="order-list">${orders.map((o, index) => { const trace = traces[index]; return `<article class="order-card"><div class="order-head"><div><p class="eyebrow">ЗАМОВЛЕННЯ ${e(o.order_number || o.id)}</p><h2>${e(orderStatus(o.status))}</h2></div><strong>${money(o.grand_total, o.currency)}</strong></div><p class="muted">${e(({ PICKUP: "Самовивіз", COURIER: "Кур’єрська доставка", POSTAL: "Поштова доставка" })[o.fulfillment_method] || o.fulfillment_method)} · ${new Date(o.created_at).toLocaleDateString("uk-UA")}</p><div class="order-items">${(o.items || []).map((i) => `<span>${e(i.product_name_snapshot)} × ${i.quantity}</span>`).join("")}</div>${trace.error ? `<p class="notice error inline">Дані платежу/доставки тимчасово недоступні: ${e(trace.error)}</p>` : `<div class="order-tracking"><b>Оплата:</b> ${e(trace.payments?.map((x) => `${orderStatus(x.status)} (${x.provider}, ${money(x.amount)})`).join(" · ") || "ще не ініційована")}<br><b>Доставка:</b> ${e(trace.delivery ? `${orderStatus(trace.delivery.status)}${trace.delivery.tracking_reference ? ` · ${trace.delivery.tracking_reference}` : ""}` : "не створена")}<br><b>Повернення:</b> ${e(trace.refunds?.map((x) => `${orderStatus(x.status)} ${money(x.amount)}`).join(" · ") || "немає")}</div>`}<div class="order-actions">${["PENDING_PAYMENT", "CONFIRMED"].includes(o.status) ? button("Оплатити (імітація)", "pay", "secondary", `data-id="${o.id}"`) : ""}${["PENDING_PAYMENT", "CONFIRMED"].includes(o.status) ? button("Скасувати замовлення", "cancel-order", "secondary", `data-id="${o.id}"`) : ""}${button("Замовити знову", "reorder", "text", `data-id="${o.id}`)}</div></article>`; }).join("")}</div>` : card(empty("Замовлень поки немає", "Ваші замовлення з’являться тут після оформлення."))}</section>`;
}

async function staffPage() {
  if (!currentUser || !["STAFF", "ADMIN"].includes(currentUser.role)) return signedOut();
  const ids = currentUser.role === "ADMIN" ? listOf(await api.request("/pharmacies/")).map((x) => x.id) : currentUser.pharmacy_ids;
  const id = Number(new URLSearchParams(location.hash.split("?")[1] || "").get("pharmacy")) || ids[0];
  const pharmacies = listOf(await api.request("/pharmacies/"));
  if (!id) return `<section class="content">${sectionHead("PHARMACY TEAM", "No assigned pharmacy", "Ask a network administrator to assign an active pharmacy to your account.")}</section>`;
  const [inventory, orders, stats] = await Promise.all([api.request(`/pharmacies/${id}/inventory/`), api.request("/orders/"), api.request(`/pharmacies/${id}/statistics/`)]);
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
  return `<section class="content">${sectionHead("NETWORK ADMINISTRATION", "Network overview", "All privileged changes are sent to the API and checked against your ADMIN role.")}<div class="stats-row">${card(`<p class="eyebrow">COMPLETED ORDER TOTAL</p><b class="stat-number">${money(data.completed_order_total)}</b>`)}${card(`<p class="eyebrow">ORDER STATUSES</p><b class="stat-number">${data.by_status?.length || 0}</b>`)}${card(`<p class="eyebrow">ACCESS</p><b class="stat-number">Administrator</b>`)}</div><div class="admin-tabs">${sections.map(([name, path], i) => `<button class="admin-tab ${i === 0 ? "active" : ""}" data-action="admin-section" data-path="${path}" data-name="${name}">${name}</button>`).join("")}<button class="admin-tab" data-action="admin-audit">Журнал аудиту</button></div><div id="admin-content" class="admin-content">${await adminTable(sections[0])}</div><div id="admin-audit-content" class="admin-content"></div></section>`;
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
    return field(e(label), key, type, false, display);
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
  const output = rows.map((r) => `<tr>${columns.map(([key]) => `<td>${e(String(r[key] ?? "—"))}</td>`).join("")}<td><button class="text-button" data-action="edit-row" data-path="${path}" data-id="${r.id}" data-columns="${e(JSON.stringify(columns))}">Edit</button></td></tr>`);
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
  return `<div class="table-toolbar"><div><p class="eyebrow">${e(label.toLocaleUpperCase("uk-UA"))}</p><h2>${data.count ?? rows.length} записів · сторінка ${pageNumber}</h2></div><button class="button secondary" data-action="toggle-create">＋ Новий запис</button></div>${rows.length ? table([...columns.map((x) => e(adminFieldLabel(x[1]).toLocaleUpperCase("uk-UA"))), ""], output) : empty("Записів немає", "Створіть перший запис за допомогою форми.")}<div class="catalog-foot"><button class="text-button" data-action="admin-page" data-path="${path}" data-name="${e(name)}" data-page="${pageNumber - 1}" ${pageNumber <= 1 ? "disabled" : ""}>← Попередня</button><span>Сторінка ${pageNumber} · ${rows.length} у списку</span><button class="text-button" data-action="admin-page" data-path="${path}" data-name="${e(name)}" data-page="${pageNumber + 1}" ${data.next ? "" : "disabled"}>Наступна →</button></div><form class="admin-create hidden" data-form="admin-create" data-path="${path}">${fields.map(([key, label, type]) => type === "checkbox" ? `<label class="check-row"><input type="checkbox" name="${key}">${e(adminFieldLabel(label))}</label>` : field(e(adminFieldLabel(label)), key, type, true)).join("")}<button class="button primary" type="submit">${createLabels[name] || "Створити запис"}</button></form>`;
}

function adminFieldLabel(label) {
  return ({ Username: "Ім’я користувача", Email: "Електронна пошта", Role: "Роль", Active: "Активний", Code: "Код", Name: "Назва", City: "Місто", Address: "Адреса", Phone: "Телефон", Description: "Опис", Category: "Категорія", Manufacturer: "Виробник", "Prescription required": "Потрібен рецепт", "Storage minimum °C": "Мінімальна температура зберігання, °C", "Storage maximum °C": "Максимальна температура зберігання, °C", "User ID": "ID користувача", "Pharmacy ID": "ID аптеки", "Promotion ID": "ID акції", "Product ID": "ID товару", "Discount rate": "Розмір знижки", "Discount rate 0–1": "Розмір знижки 0–1", "Bonus rate": "Бонусна ставка", "Bonus rate 0–1": "Бонусна ставка 0–1", "Starts at": "Початок дії", "Ends at": "Кінець дії", Method: "Спосіб", Enabled: "Увімкнено", "Requires cold chain": "Потрібен холодовий ланцюг", "Cold chain supported": "Холодовий ланцюг доступний", "Staff user ID": "ID працівника", "Method: PICKUP, COURIER, POSTAL": "Спосіб: PICKUP, COURIER, POSTAL" })[label] || label;
}

function authRequired() { return "Please sign in before continuing."; }

root.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]"); if (!target) return;
  const action = target.dataset.action;
  if (["logout", "add", "remove", "update-cart", "cancel-order", "reorder", "pay", "transition", "ship", "verify-prescription", "refund", "read-notification", "delete-prescription", "watch-product", "toggle-watch", "edit-row", "confirm-order"].includes(action)) target.disabled = true;
  try {
    if (action === "dismiss") { message = ""; render(); }
    if (action === "confirm-order") { await confirmOrder(); }
    if (action === "back-to-cart") { pendingOrder = null; render(); }
    if (action === "retry") render();
    if (action === "next-page") { catalogPageNumber += 1; render(); }
    if (action === "previous-page") { catalogPageNumber = Math.max(1, catalogPageNumber - 1); render(); }
    if (action === "logout") { auth.clear(); currentUser = null; flash("You have signed out."); location.hash = "home"; render(); }
    if (action === "menu") document.querySelector(".main-nav")?.classList.toggle("open");
    if (action === "add") await changeCart(Number(target.dataset.id), 1);
    if (action === "remove") await changeCart(Number(target.dataset.id), 0);
    if (action === "update-cart") { for (const input of document.querySelectorAll("[data-quantity]")) await changeCart(Number(input.dataset.quantity), Number(input.value)); flash("Bag updated from the pharmacy API."); render(); }
    if (action === "inventory") { const data = await api.request(`/pharmacies/${target.dataset.id}/inventory/`, { auth: false }); document.querySelector(`#stock-${target.dataset.id}`).innerHTML = listOf(data).map((x) => `<p>${e(x.product__name)} · ${x.available} available · ${money(x.unit_price)}</p>`).join("") || "No listed stock"; }
    if (action === "cancel-order") { if (!window.confirm("Скасувати замовлення? API може автоматично звільнити резерв товару та запустити повернення платежу.")) { target.disabled = false; return; } await api.request(`/orders/${target.dataset.id}/transition/`, { method: "POST", body: { status: "CANCELLED" } }); flash("Запит на скасування підтверджено сервером."); render(); }
    if (action === "reorder") { await api.request(`/orders/${target.dataset.id}/reorder/`, { method: "POST", body: {} }); flash("Items copied to your cart. Request a fresh quote before ordering."); location.hash = "cart"; render(); }
    if (action === "pay") { await api.request(`/orders/${target.dataset.id}/pay/`, { method: "POST", body: { idempotency_key: crypto.randomUUID() } }); flash("Simulated payment request queued. Refresh the order later for its status."); render(); }
    if (action === "fulfillment") { const data = await api.request(`/orders/${target.dataset.id}/fulfillment/`); const box = document.querySelector(`#fulfillment-${target.dataset.id}`); box.innerHTML = `<pre>${e(JSON.stringify(data, null, 2))}</pre>`; }
    if (action === "transition") { await api.request(`/orders/${target.dataset.id}/transition/`, { method: "POST", body: { status: target.dataset.status } }); flash("Order status updated by the API."); render(); }
    if (action === "ship") { await api.request(`/orders/${target.dataset.id}/ship/`, { method: "POST", body: {} }); flash("Shipment request queued."); render(); }
    if (action === "verify-prescription") { const approved = target.dataset.approved === "true"; await api.request(`/orders/${target.dataset.id}/verify-prescription/`, { method: "POST", body: { approved } }); flash(approved ? "Рецепт перевірено та схвалено." : "Рецепт відхилено."); render(); }
    if (action === "refund") { const amount = prompt("Сума повернення (UAH)"); if (amount && Number(amount) > 0) { const reason = prompt("Причина повернення"); if (reason) { await api.request(`/orders/${target.dataset.id}/refund/`, { method: "POST", body: { amount, reason, idempotency_key: crypto.randomUUID() } }); flash("Запит на імітоване повернення прийнято."); render(); } } }
    if (action === "audit") { const data = await api.request(`/pharmacies/${target.dataset.id}/audit/`); document.querySelector(`#audit-${target.dataset.id}`).innerHTML = `<pre>${e(JSON.stringify(data, null, 2))}</pre>`; }
    if (action === "admin-audit") { const data = await api.request("/admin/audit/"); document.querySelector("#admin-audit-content").innerHTML = table(["ID", "ACTOR", "ACTION", "TARGET", "WHEN"], listOf(data).map((x) => `<tr><td>${x.id}</td><td>${e(x.actor_id ?? "—")}</td><td>${e(x.action)}</td><td>${e(x.target_type)} ${e(x.target_id ?? "")}</td><td>${e(new Date(x.occurred_at).toLocaleString("uk-UA"))}</td></tr>`)); }
    if (action === "read-notification") { await api.request(`/notifications/${target.dataset.id}/read/`, { method: "POST", body: {} }); flash("Notification marked as read."); render(); }
    if (action === "delete-prescription") { if (!window.confirm("Видалити збережену позначку рецепта?")) { target.disabled = false; return; } await api.request(`/prescriptions/${target.dataset.id}/`, { method: "DELETE" }); flash("Позначку рецепта видалено."); render(); }
    if (action === "toggle-create") document.querySelector(".admin-create")?.classList.toggle("hidden");
    if (action === "close-dialog") target.closest("dialog")?.close();
    if (action === "admin-section") { const name = target.dataset.name; const section = adminSections.find((x) => x[0] === name); if (section) document.querySelector("#admin-content").innerHTML = await adminTable(section); document.querySelectorAll(".admin-tab").forEach((b) => b.classList.toggle("active", b === target)); }
    if (action === "admin-page") { const section = adminSections.find((x) => x[1] === target.dataset.path); if (section && Number(target.dataset.page) > 0) document.querySelector("#admin-content").innerHTML = await adminTable(section, Number(target.dataset.page)); }
    if (action === "watch-product") { const pharmacyId = Number(document.querySelector("#watch-pharmacy")?.value); if (!pharmacyId) throw new Error("Для цього товару немає аптеки з відкритою наявністю."); await api.request("/availability-watches/", { method: "POST", body: { product_id: Number(target.dataset.id), pharmacy_id: pharmacyId, is_active: true } }); flash("Підписку наявності збережено через API."); render(); }
    if (action === "toggle-watch") { await api.request("/availability-watches/", { method: "POST", body: { product_id: Number(target.dataset.product), pharmacy_id: Number(target.dataset.pharmacy), is_active: target.dataset.active !== "true" } }); flash("Налаштування підписки збережено."); render(); }
    if (action === "edit-row") await editAdminRow(target);
  } catch (error) { flash(error.message, "error"); render(); }
});

root.addEventListener("change", (event) => {
  if (event.target.matches("[data-action='branch-select']")) { location.hash = `staff?pharmacy=${event.target.value}`; }
  if (event.target.name === "fulfillment_method") { const group = document.querySelector(".recipient-fields"); group?.classList.toggle("hidden", event.target.value === "PICKUP"); for (const input of group?.querySelectorAll("input") || []) input.required = event.target.value !== "PICKUP"; }
});

root.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-form]"); if (!form) return;
  event.preventDefault();
  const kind = form.dataset.form;
  const submitButton = form.querySelector('[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  const formData = new FormData(form);
  const raw = Object.fromEntries(formData.entries());
  try {
    if (kind === "filters") { catalogFilters = { search: raw.search.trim(), category: raw.category, manufacturer: raw.manufacturer }; catalogPageNumber = 1; render(); }
    if (kind === "login") { currentUser = await auth.signIn(raw.username, raw.password); flash("Welcome back."); location.hash = currentUser.role === "ADMIN" ? "admin" : currentUser.role === "STAFF" ? "staff" : "account"; render(); }
    if (kind === "register") { currentUser = await auth.register(raw); flash("Your customer account is ready."); location.hash = "account"; render(); }
    if (kind === "profile") { await api.request("/profile/", { method: "PATCH", body: { full_name: raw.full_name, phone: raw.phone || null, preferred_pharmacy_id: raw.preferred_pharmacy_id ? Number(raw.preferred_pharmacy_id) : null } }); flash("Profile saved."); render(); }
    if (kind === "preferences") { await api.request("/preferences/", { method: "POST", body: { promotions_enabled: form.elements.promotions_enabled.checked, reminders_enabled: form.elements.reminders_enabled.checked } }); flash("Preferences saved."); render(); }
    if (kind === "prescription") { await api.request("/prescriptions/", { method: "POST", body: { display_label: raw.display_label } }); flash("Demo label saved."); render(); }
    if (kind === "reminder") { const nextRun = new Date(raw.next_run_at); if (nextRun <= new Date()) throw new Error("Дата нагадування має бути в майбутньому."); await api.request("/reminders/", { method: "POST", body: { product_id: Number(raw.product_id), interval_days: Number(raw.interval_days), next_run_at: nextRun.toISOString(), is_active: true } }); flash("Нагадування збережено через API."); render(); }
    if (kind === "stock") { const body = {}; if (raw.adjustment) body.adjustment = Number(raw.adjustment); if (raw.unit_price) body.unit_price = raw.unit_price; const listed = form.elements.is_listed.checked; if (String(listed) !== form.dataset.listed) body.is_listed = listed; if (!Object.keys(body).length) throw new Error("Вкажіть зміну залишку, ціни або доступності товару."); await api.request(`/pharmacies/${form.dataset.pharmacy}/inventory/${form.dataset.product}/`, { method: "PATCH", body }); flash("Зміни залишку підтверджено сервером."); render(); }
    if (kind === "admin-create") { const body = Object.fromEntries(Object.entries(raw).filter(([key, v]) => form.elements[key]?.type === "checkbox" || v !== "")); for (const box of form.querySelectorAll('input[type="checkbox"]')) body[box.name] = box.checked; for (const key of ["category", "manufacturer", "user", "pharmacy", "promotion", "product"]) if (body[key]) body[key] = Number(body[key]); for (const key of ["discount_rate", "bonus_rate", "storage_min_c", "storage_max_c", "max_storage_min_c", "min_storage_max_c"]) if (body[key] !== "") body[key] = Number(body[key]); if (body.starts_at) body.starts_at = new Date(body.starts_at).toISOString(); if (body.ends_at) body.ends_at = new Date(body.ends_at).toISOString(); const path = form.dataset.path; if (["/admin/users/", "/pharmacies/", "/admin/assignments/", "/admin/promotions/"].includes(path)) body.is_active = true; if (path === "/products/") body.is_active = true; await api.request(path, { method: "POST", body }); flash("Запис створено на сервері."); render(); }
    if (kind === "admin-edit") { const body = {}; for (const input of form.querySelectorAll("input")) { const key = input.name; if (!key) continue; if (input.type === "checkbox") body[key] = input.checked; else if (input.value === "") body[key] = ["storage_min_c", "storage_max_c"].includes(key) ? null : ""; else if (input.type === "number") body[key] = Number(input.value); else if (key.endsWith("_at")) body[key] = new Date(input.value).toISOString(); else body[key] = input.value; } await api.request(`${form.dataset.path}${form.dataset.id}/`, { method: "PATCH", body }); form.closest("dialog")?.close(); flash("Зміни збережено на сервері."); render(); }
    if (kind === "checkout") await checkout(raw);
  } catch (error) { flash(error.message, "error"); render(); }
});

async function changeCart(productId, quantity) {
  if (currentUser && currentUser.role !== "CUSTOMER") throw new Error("Кошик доступний лише гостям і клієнтам.");
  const guest = !auth.token;
  await api.request(guest ? "/guest-cart/" : "/cart/", { method: "PUT", auth: !guest, body: { product_id: productId, quantity } });
  flash(quantity ? "Added to your bag." : "Removed from your bag.");
  if (page() === "cart") render(); else root.querySelector(".notice")?.remove();
}

async function checkout(raw) {
  if (!currentUser) { flash("Sign in to request a live quote and place an order.", "info"); location.hash = "login"; render(); return; }
  if (currentUser.role !== "CUSTOMER") throw new Error("Оформити замовлення може лише клієнтський обліковий запис.");
  const cart = await api.request("/cart/");
  const lines = cart.items || [];
  if (!lines.length) throw new Error("Your customer cart is empty. Add items and update your bag first.");
  const quoteBody = { pharmacy_id: Number(raw.pharmacy_id), fulfillment_method: raw.fulfillment_method, items: lines };
  const quote = await api.request("/checkout/quote/", { method: "POST", body: quoteBody });
  const quoteItems = quote.lines || [];
  pendingOrder = {
    body: { ...quoteBody, payment_method: raw.payment_method, expected_total: quote.grand_total, items: quoteItems.map((item) => ({ product_id: item.product_id, quantity: item.quantity, expected_unit_price: item.price })), ...(raw.fulfillment_method !== "PICKUP" ? { recipient: { name: raw.recipient_name, phone: raw.recipient_phone, destination: raw.recipient_destination } } : {}) },
    quote,
  };
  const quoteRows = quoteItems.map((item) => `<tr><td>${e(item.name)}</td><td>${item.quantity}</td><td>${money(item.price)}</td><td>${money(Number(item.price) * item.quantity)}</td></tr>`);
  const content = `<section class="content narrow">${sectionHead("CHECKOUT", "Перевірте розрахунок аптеки", "Підсумкову суму розрахував сервер за актуальними цінами та залишками.")}${card(`${table(["ТОВАР", "КІЛЬКІСТЬ", "ЦІНА", "РАЗОМ"], quoteRows)}<dl class="quote-totals"><div><dt>Сума товарів</dt><dd>${money(quote.subtotal)}</dd></div><div><dt>Знижка</dt><dd>− ${money(quote.discount)}</dd></div><div><dt>Доставка</dt><dd>${money(quote.shipping)}</dd></div><div class="quote-grand"><dt>Разом до сплати</dt><dd>${money(quote.grand_total)}</dd></div></dl><p class="fine-print">Спосіб оплати: ${e(raw.payment_method)} · Після підтвердження API повторно перевірить ціну та залишки.</p><div class="button-row"><button class="button secondary" data-action="back-to-cart">Повернутися до кошика</button><button class="button primary" data-action="confirm-order">Підтвердити замовлення</button></div>`)}</section>`;
  root.innerHTML = localizeMarkup(shell(content));
}

async function confirmOrder() {
  if (!pendingOrder) throw new Error("Спочатку отримайте актуальний розрахунок замовлення.");
  const order = await api.request("/orders/", { method: "POST", body: pendingOrder.body });
  pendingOrder = null;
  flash(`Замовлення ${order.order_number || order.id} створено зі станом ${order.status}.`);
  location.hash = "orders";
  render();
}

render();
