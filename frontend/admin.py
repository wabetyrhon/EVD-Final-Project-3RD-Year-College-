"""Admin dashboard (PyScript) for the Flask API.

API used (admin session required for changes):
  GET /api/categories, GET /api/products, POST/PUT/DELETE /api/products[/<id>]
  GET /api/reservations, PUT/DELETE /api/reservations/<id>
Events: click (one handler for every button, using data-action) and input (search and filters).
"""
import json
import js
from pyscript import document, window, when
from pyscript.ffi import create_proxy

VIEWS = {"overview": "Overview", "products": "Products", "reservations": "Reservations"}

categories = []  # [{"category_id", "name"}]
products = []
reservations = []
pending = {}  # delete waiting for confirmation
CHANGE_DAYS = 14  # same as the customer page


# ---------- helpers ----------
def q(sel):
    return document.querySelector(sel)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def money(n):
    return "₱{:,.2f}".format(float(n or 0))


def local_today():
    d = js.Date.new()
    return "%04d-%02d-%02d" % (d.getFullYear(), d.getMonth() + 1, d.getDate())


def toast(text, bad=False):
    t = q("#toast")
    t.innerText = text
    t.className = "show bad" if bad else "show"
    window.setTimeout(create_proxy(lambda: t.classList.remove("show")), 2600)


def show_banner(html):
    b = q("#banner")
    b.innerHTML = html
    b.classList.remove("hidden")


def hide_banner():
    q("#banner").classList.add("hidden")


def error_text(data, status):
    if isinstance(data, dict) and data.get("error"):
        return str(data["error"])
    if status in (401, 403):
        return "Your session expired. Please log in again."
    return "The server returned an error (%s)." % status


def set_err(prefix, field, msg):
    q("#%s-err-%s" % (prefix, field)).innerText = msg
    q("#%s-%s" % (prefix, field)).setAttribute("aria-invalid", "true" if msg else "false")


async def api(url, method="GET", body=None):
    init = js.Object.new()
    init.method = method
    headers = js.window.Headers.new()
    headers.set("Content-Type", "application/json")
    init.headers = headers
    if body is not None:
        init.body = json.dumps(body)
    res = await js.window.fetch(url, init)
    data = None
    try:
        raw = await res.json()
        data = raw.to_py() if hasattr(raw, "to_py") else raw
    except Exception:
        data = None
    return res.ok, res.status, data


def product_by_id(pid):
    for p in products:
        if str(p["product_id"]) == str(pid):
            return p


def res_by_id(rid):
    for r in reservations:
        if str(r["reservation_id"]) == str(rid):
            return r


def cat_name(cid):
    for c in categories:
        if str(c["category_id"]) == str(cid):
            return c["name"]
    return "Uncategorized"


def res_total(r):
    total = 0
    for it in r.get("items", []):
        p = product_by_id(it["product_id"])
        if p and p.get("price") is not None:
            total += p["price"] * it["quantity"]
    return total


def price_chip(p):
    """Same badge customers see: the old price with an arrow, for recent changes."""
    prev = p.get("previous_price")
    if prev is None or p.get("price") is None or prev == p["price"]:
        return ""
    when_changed = p.get("price_changed_at")
    if when_changed and (js.Date.now() - js.Date.new(when_changed).getTime()) / 86400000 > CHANGE_DAYS:
        return ""
    up = p["price"] > prev
    return '<span class="chg %s"><span aria-hidden="true">%s</span>%s, was <s>%s</s></span>' % (
        "up" if up else "down", "▲" if up else "▼", "Raised" if up else "Lowered", money(prev))


def date_badge(d, today):
    if not d:
        return '<span class="badge past">Not set</span>'
    if d == today:
        return '<span class="badge today">Today</span>'
    if d > today:
        return '<span class="badge up">Upcoming</span>'
    return '<span class="badge past">Past</span>'


# ---------- loading ----------
async def fetch_list(url):
    try:
        ok, status, data = await api(url)
    except Exception:
        return None
    return data if ok and isinstance(data, list) else None


async def load_all():
    global categories, products, reservations
    cats = await fetch_list("/api/categories")
    prods = await fetch_list("/api/products")
    ress = await fetch_list("/api/reservations")
    if prods is None or ress is None:
        show_banner('Could not load data. Check that the server is running or <a href="/login">log in again</a>.')
    else:
        hide_banner()
    categories = cats or []
    products = prods or []
    reservations = ress or []
    render_all()


# ---------- rendering ----------
def render_all():
    q("#nav-products-count").innerText = str(len(products))
    q("#nav-res-count").innerText = str(len(reservations))
    fill_category_options()
    render_overview()
    render_products()
    render_reservations()


def fill_category_options():
    keep = q("#prod-cat-filter").value
    opts = '<option value="">All categories</option>'
    form_opts = '<option value="">Select a category</option>'
    for c in categories:
        o = '<option value="%s">%s</option>' % (esc(c["category_id"]), esc(c["name"]))
        opts += o
        form_opts += o
    q("#prod-cat-filter").innerHTML = opts
    q("#prod-cat-filter").value = keep
    q("#pf-category").innerHTML = form_opts


def render_overview():
    today = local_today()
    upcoming = [r for r in reservations if r.get("pickup_date") and r["pickup_date"] >= today]
    upcoming.sort(key=lambda r: r["pickup_date"])
    q("#stat-products").innerText = str(len(products))
    q("#stat-res").innerText = str(len(reservations))
    q("#stat-today").innerText = str(len([r for r in reservations if r.get("pickup_date") == today]))
    q("#stat-value").innerText = money(sum(res_total(r) for r in upcoming))
    if not upcoming:
        q("#upcoming-list").innerHTML = '<p class="empty-row">No upcoming pickups yet.</p>'
        return
    html = ""
    for r in upcoming[:6]:
        html += (
            '<div class="list-row"><div><strong>%s</strong><span class="muted rid">%s</span></div>'
            "<div>%s %s</div><div><strong>%s</strong></div>"
            '<button class="btn small ghost" data-action="view-res" data-id="%s">View</button></div>'
        ) % (esc(r["customer_name"]), esc(r["reservation_id"]), esc(r["pickup_date"]),
             date_badge(r["pickup_date"], today), money(res_total(r)), esc(r["reservation_id"]))
    q("#upcoming-list").innerHTML = html


def render_products():
    term = q("#prod-search").value.strip().lower()
    cat = q("#prod-cat-filter").value
    html = ""
    shown = 0
    for p in products:
        if term and term not in p["name"].lower():
            continue
        if cat and str(p.get("category_id")) != cat:
            continue
        shown += 1
        img = p.get("img_url") or ""
        thumb = '<div class="thumb"><span>No image</span>%s</div>' % (
            '<img src="%s" alt="" onerror="this.remove()">' % esc(img) if img else "")
        price = money(p["price"]) if p.get("price") is not None else "Not set"
        chip = price_chip(p)
        if chip:
            price += "<br>" + chip
        pid = esc(p["product_id"])
        html += (
            "<tr><td>%s</td><td><strong>%s</strong></td><td>%s</td><td>%s</td><td>%s</td>"
            '<td class="actions"><button class="btn small ghost" data-action="edit-product" data-id="%s">Edit</button>'
            '<button class="btn small danger" data-action="delete-product" data-id="%s">Delete</button></td></tr>'
        ) % (thumb, esc(p["name"]), esc(cat_name(p.get("category_id"))), price, esc(p["unit"]), pid, pid)
    q("#products-body").innerHTML = html or '<tr><td colspan="6" class="empty-row">No products match.</td></tr>'
    q("#prod-count").innerText = "Showing %d of %d products" % (shown, len(products))


def render_reservations():
    today = local_today()
    term = q("#res-search").value.strip().lower()
    mode = q("#res-date-filter").value
    rows = sorted(reservations, key=lambda r: r.get("created_at") or "", reverse=True)
    html = ""
    shown = 0
    for r in rows:
        d = r.get("pickup_date")
        if mode == "today" and d != today:
            continue
        if mode == "upcoming" and not (d and d > today):
            continue
        if mode == "past" and not (d and d < today):
            continue
        if mode == "none" and d:
            continue
        hay = " ".join(str(r.get(k) or "") for k in ("reservation_id", "customer_name", "customer_email", "customer_phone")).lower()
        if term and term not in hay:
            continue
        shown += 1
        rid = esc(r["reservation_id"])
        html += (
            '<tr><td><span class="rid">%s</span><br><button class="link" data-action="copy" data-text="%s">Copy</button></td>'
            '<td><strong>%s</strong><br><span class="muted">%s<br>%s</span></td>'
            "<td>%s<br>%s</td><td>%d items<br><strong>%s</strong></td>"
            '<td class="actions"><button class="btn small ghost" data-action="view-res" data-id="%s">View</button>'
            '<button class="btn small ghost" data-action="edit-res" data-id="%s">Edit</button>'
            '<button class="btn small danger" data-action="delete-res" data-id="%s">Delete</button></td></tr>'
        ) % (rid, rid, esc(r["customer_name"]), esc(r["customer_email"]), esc(r["customer_phone"]),
             esc(d or "Not set"), date_badge(d, today), len(r.get("items", [])), money(res_total(r)), rid, rid, rid)
    q("#reservations-body").innerHTML = html or '<tr><td colspan="5" class="empty-row">No reservations match.</td></tr>'
    q("#res-count").innerText = "Showing %d of %d reservations" % (shown, len(reservations))


def show_view(name):
    if name not in VIEWS:
        name = "overview"
    for v in VIEWS:
        q("#view-" + v).classList.add("hidden")
    q("#view-" + name).classList.remove("hidden")
    for el in document.querySelectorAll(".nav-link"):
        if el.getAttribute("data-view") == name:
            el.classList.add("active")
        else:
            el.classList.remove("active")
    q("#page-title").innerText = VIEWS[name]
    window.location.hash = name


# ---------- product dialog ----------
def update_preview():
    url = q("#pf-img").value.strip()
    q("#pf-preview").innerHTML = "<span>No image</span>" + (
        '<img src="%s" alt="" onerror="this.remove()">' % esc(url) if url else "")


def open_product_dialog(pid):
    for f in ("name", "unit", "price", "category"):
        set_err("pf", f, "")
    q("#pf-error").innerText = ""
    p = product_by_id(pid) if pid else None
    q("#pf-title").innerText = "Edit product" if p else "Add product"
    q("#pf-id").value = str(p["product_id"]) if p else ""
    q("#pf-name").value = p["name"] if p else ""
    q("#pf-unit").value = p["unit"] if p else ""
    q("#pf-price").value = str(p["price"]) if p and p.get("price") is not None else ""
    q("#pf-category").value = str(p["category_id"]) if p and p.get("category_id") is not None else ""
    q("#pf-img").value = (p.get("img_url") or "") if p else ""
    update_preview()
    q("#product-dialog").showModal()


async def save_product():
    name = q("#pf-name").value.strip()
    unit = q("#pf-unit").value.strip()
    cat = q("#pf-category").value
    img = q("#pf-img").value.strip()
    try:
        price = float(q("#pf-price").value)
    except Exception:
        price = None
    errs = {
        "name": "" if name else "Enter the product name.",
        "unit": "" if unit else "Enter the unit, like 1 kg.",
        "price": "" if price is not None and price >= 0 else "Enter a price of 0 or more.",
        "category": "" if cat else "Choose a category.",
    }
    for f in errs:
        set_err("pf", f, errs[f])
    if any(errs.values()):
        return
    pid = q("#pf-id").value
    payload = {"name": name, "unit": unit, "price": price, "category_id": int(cat), "img_url": img}
    btn = q("#pf-save")
    btn.disabled = True
    btn.innerText = "Saving..."
    q("#pf-error").innerText = ""
    try:
        if pid:
            ok, status, data = await api("/api/products/%s" % pid, "PUT", payload)
        else:
            ok, status, data = await api("/api/products", "POST", payload)
    except Exception:
        ok, status, data = False, 0, {"error": "Could not reach the server."}
    btn.disabled = False
    btn.innerText = "Save product"
    if ok:
        q("#product-dialog").close()
        toast("Product saved")
        await load_all()
    else:
        q("#pf-error").innerText = error_text(data, status)


# ---------- reservation dialogs ----------
def open_res_view(rid):
    r = res_by_id(rid)
    if not r:
        return
    today = local_today()
    lines = ""
    total = 0
    for it in r.get("items", []):
        p = product_by_id(it["product_id"])
        if p:
            name = "%s (%s)" % (p["name"], p["unit"])
            price = p.get("price")
        else:
            name = "Product #%s (removed)" % it["product_id"]
            price = None
        sub = (price or 0) * it["quantity"]
        total += sub
        lines += '<tr><td>%s</td><td class="r">x%s</td><td class="r">%s</td></tr>' % (
            esc(name), it["quantity"], money(sub) if price is not None else "-")
    placed = (r.get("created_at") or "")[:16].replace("T", " ")
    rid_e = esc(r["reservation_id"])
    q("#res-view-dialog").innerHTML = (
        '<div class="dlg-inner"><div class="dlg-head"><h3>Reservation</h3>'
        '<button class="x" data-action="close" data-target="res-view-dialog" aria-label="Close">&times;</button></div>'
        '<p class="rid">%s</p>'
        '<dl class="facts-lite"><dt>Customer</dt><dd>%s</dd><dt>Email</dt><dd>%s</dd><dt>Mobile</dt><dd>%s</dd>'
        "<dt>Pickup</dt><dd>%s %s</dd><dt>Placed</dt><dd>%s</dd></dl>"
        '<table class="items"><tbody>%s</tbody></table>'
        '<p class="total-row"><span>Total</span><span>%s</span></p>'
        '<div class="dlg-foot"><button class="btn ghost" data-action="edit-res" data-id="%s">Edit details</button>'
        '<button class="btn" data-action="close" data-target="res-view-dialog">Done</button></div></div>'
    ) % (rid_e, esc(r["customer_name"]), esc(r["customer_email"]), esc(r["customer_phone"]),
         esc(r.get("pickup_date") or "Not set"), date_badge(r.get("pickup_date"), today), esc(placed or "-"),
         lines, money(total), rid_e)
    q("#res-view-dialog").showModal()


def open_res_edit(rid):
    r = res_by_id(rid)
    if not r:
        return
    q("#res-view-dialog").close()
    for f in ("name", "email", "phone"):
        set_err("re", f, "")
    q("#re-error").innerText = ""
    q("#re-id").value = str(r["reservation_id"])
    q("#re-rtn").innerText = str(r["reservation_id"])
    q("#re-name").value = r["customer_name"]
    q("#re-email").value = r["customer_email"]
    q("#re-phone").value = r["customer_phone"]
    q("#re-date").value = r.get("pickup_date") or ""
    q("#res-edit-dialog").showModal()


async def save_res():
    name = q("#re-name").value.strip()
    email = q("#re-email").value.strip()
    phone = q("#re-phone").value.strip()
    errs = {
        "name": "" if name else "Enter the customer name.",
        "email": "" if "@" in email and "." in email.split("@")[-1] else "Enter a valid email.",
        "phone": "" if phone else "Enter a mobile number.",
    }
    for f in errs:
        set_err("re", f, errs[f])
    if any(errs.values()):
        return
    payload = {"customer_name": name, "customer_email": email, "customer_phone": phone,
               "pickup_date": q("#re-date").value}
    btn = q("#re-save")
    btn.disabled = True
    btn.innerText = "Saving..."
    try:
        ok, status, data = await api("/api/reservations/%s" % q("#re-id").value, "PUT", payload)
    except Exception:
        ok, status, data = False, 0, {"error": "Could not reach the server."}
    btn.disabled = False
    btn.innerText = "Save changes"
    if ok:
        q("#res-edit-dialog").close()
        toast("Reservation updated")
        await load_all()
    else:
        q("#re-error").innerText = error_text(data, status)


# ---------- delete with confirmation ----------
def ask_delete(kind, key, title, message):
    pending["kind"] = kind
    pending["key"] = key
    q("#confirm-dialog").innerHTML = (
        '<div class="dlg-inner"><div class="dlg-head"><h3>%s</h3></div><p>%s</p>'
        '<div class="dlg-foot"><button class="btn ghost" data-action="close" data-target="confirm-dialog">Cancel</button>'
        '<button class="btn bad" data-action="confirm-yes">Delete</button></div></div>'
    ) % (esc(title), esc(message))
    q("#confirm-dialog").showModal()


async def do_delete():
    kind, key = pending.get("kind"), pending.get("key")
    q("#confirm-dialog").close()
    url = "/api/products/%s" % key if kind == "product" else "/api/reservations/%s" % key
    try:
        ok, status, data = await api(url, "DELETE")
    except Exception:
        ok, status, data = False, 0, {"error": "Could not reach the server."}
    if ok:
        toast("Deleted")
        await load_all()
    else:
        toast(error_text(data, status), True)


# ---------- events ----------
@when("click", "body")
async def on_click(event):
    t = event.target
    if t.tagName == "DIALOG" and t.hasAttribute("data-bd"):
        t.close()  # click on the dark area outside a view or confirm popup
        return
    el = t.closest("[data-action]")
    if not el:
        return
    act = el.getAttribute("data-action")
    key = el.getAttribute("data-id")
    if act == "nav":
        show_view(el.getAttribute("data-view"))
    elif act == "close":
        q("#" + el.getAttribute("data-target")).close()
    elif act == "add-product":
        open_product_dialog(None)
    elif act == "edit-product":
        open_product_dialog(key)
    elif act == "save-product":
        await save_product()
    elif act == "delete-product":
        p = product_by_id(key)
        ask_delete("product", key, "Delete product", "Delete %s? This cannot be undone." % (p["name"] if p else "this product"))
    elif act == "view-res":
        open_res_view(key)
    elif act == "edit-res":
        open_res_edit(key)
    elif act == "save-res":
        await save_res()
    elif act == "delete-res":
        r = res_by_id(key)
        q("#res-view-dialog").close()
        ask_delete("reservation", key, "Delete reservation", "Delete the reservation of %s? This cannot be undone." % (r["customer_name"] if r else "this customer"))
    elif act == "confirm-yes":
        await do_delete()
    elif act == "copy":
        window.navigator.clipboard.writeText(el.getAttribute("data-text"))
        toast("RTN copied")


@when("input", "body")
def on_input(event):
    i = event.target.id
    if i in ("prod-search", "prod-cat-filter"):
        render_products()
    elif i in ("res-search", "res-date-filter"):
        render_reservations()
    elif i == "pf-img":
        update_preview()


# ---------- startup ----------
show_view(window.location.hash[1:] if window.location.hash else "overview")
await load_all()
