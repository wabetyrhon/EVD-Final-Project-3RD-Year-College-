"""Frozen meat shop - PyScript logic (event-driven).

Events: click on categories, products, cart +/-, reserve, track, owner actions.
Reservations are saved in the browser's localStorage under KEY.
"""
import json
import random
from pyscript import document, window, when
from pyscript.ffi import create_proxy

CATEGORIES = [
    {"id": "pork", "name": "Pork"},
    {"id": "chicken", "name": "Chicken"},
    {"id": "tuna", "name": "Tuna"},
]
# Placeholder products: edit names, prices and details. Photos: assets/products/<id>.jpg
PRODUCTS = [
    {"id": "pork-belly", "cat": "pork", "name": "Pork Belly", "price": 320, "desc": "Skin-on slab, good for liempo and lechon kawali.", "pack": "Vacuum-packed, about 1 kg", "stock": "In stock"},
    {"id": "pork-chop", "cat": "pork", "name": "Pork Chop", "price": 290, "desc": "Bone-in cuts for frying or grilling.", "pack": "Vacuum-packed, about 1 kg", "stock": "In stock"},
    {"id": "ground-pork", "cat": "pork", "name": "Ground Pork", "price": 260, "desc": "Fine grind for embutido and meatballs.", "pack": "Bagged, 500 g or 1 kg", "stock": "In stock"},
    {"id": "whole-chicken", "cat": "chicken", "name": "Whole Chicken", "price": 210, "desc": "Cleaned whole dressed chicken.", "pack": "Bagged, about 1.2 kg each", "stock": "In stock"},
    {"id": "chicken-breast", "cat": "chicken", "name": "Chicken Breast", "price": 240, "desc": "Skinless, boneless breast fillet.", "pack": "Bagged, 1 kg", "stock": "In stock"},
    {"id": "chicken-wings", "cat": "chicken", "name": "Chicken Wings", "price": 230, "desc": "Party wings, cut and cleaned.", "pack": "Bagged, 1 kg", "stock": "In stock"},
    {"id": "tuna-steak", "cat": "tuna", "name": "Tuna Steak", "price": 380, "desc": "Thick-cut steaks for grilling or searing.", "pack": "Vacuum-packed, about 1 kg", "stock": "In stock"},
    {"id": "tuna-belly", "cat": "tuna", "name": "Tuna Belly", "price": 420, "desc": "Fatty belly cut, great grilled.", "pack": "Vacuum-packed, about 1 kg", "stock": "In stock"},
    {"id": "tuna-cubes", "cat": "tuna", "name": "Tuna Cubes", "price": 350, "desc": "Pre-cut cubes for kinilaw and skewers.", "pack": "Bagged, 500 g or 1 kg", "stock": "In stock"},
]
OWNER_PIN = "owner123"  # demo only - change it
KEY = "laortealbe_reservations"
CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

cart = {}  # product id -> kilos
owner_unlocked = False


# ---------- helpers ----------
def q(sel):
    return document.querySelector(sel)


def peso(n):
    return "₱" + "%.2f" % n


def kg_text(kg):
    return str(int(kg)) if kg == int(kg) else str(kg)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def product(pid):
    for p in PRODUCTS:
        if p["id"] == pid:
            return p


def photo(src, label):
    return '<div class="photo">%s<img src="%s" alt="" onerror="this.remove()"></div>' % (label, src)


def toast(text):
    t = q("#toast")
    t.innerText = text
    t.classList.add("show")
    window.setTimeout(create_proxy(lambda: t.classList.remove("show")), 2400)


def load_orders():
    raw = window.localStorage.getItem(KEY)
    return json.loads(raw) if raw else []


def save_orders(orders):
    window.localStorage.setItem(KEY, json.dumps(orders))


def new_rtn(orders):
    used = [o["rtn"] for o in orders]
    while True:
        code = "LMS-" + "".join(CHARS[random.randint(0, len(CHARS) - 1)] for _ in range(6))
        if code not in used:
            return code


def cart_total():
    return sum(product(pid)["price"] * kg for pid, kg in cart.items())


def badge(status):
    cls = {"Verified": "ok", "Cancelled": "no"}.get(status, "")
    return '<span class="badge %s">%s</span>' % (cls, status)


def items_text(items):
    return ", ".join("%s %s kg" % (i["name"], kg_text(i["kg"])) for i in items)


def set_error(field, text):
    q("#err-" + field).innerText = text
    q("#cust-" + field).setAttribute("aria-invalid", "true" if text else "false")


# ---------- rendering ----------
def render_categories():
    html = ""
    for c in CATEGORIES:
        n = len([p for p in PRODUCTS if p["cat"] == c["id"]])
        html += (
            '<button class="cat-card" data-cat="%s">%s<h3>%s</h3><p>%d products</p></button>'
        ) % (c["id"], photo("assets/categories/%s.jpg" % c["id"], "Category photo"), c["name"], n)
    q("#category-grid").innerHTML = html


def show_category(cid):
    name = [c["name"] for c in CATEGORIES if c["id"] == cid][0]
    html = ""
    for p in [p for p in PRODUCTS if p["cat"] == cid]:
        html += (
            '<article class="pcard"><button class="pcard-main" data-open="%s" aria-label="View details for %s">'
            "%s<h3>%s</h3></button>"
            '<div class="meta"><span class="price">%s / kg</span>'
            '<button class="btn small" data-add="%s">Add</button></div></article>'
        ) % (p["id"], p["name"], photo("assets/products/%s.jpg" % p["id"], "Product photo"),
             p["name"], peso(p["price"]), p["id"])
    q("#product-grid").innerHTML = html
    q("#product-title").innerText = name
    q("#category-view").classList.add("hidden")
    q("#product-view").classList.remove("hidden")
    q("#products").scrollIntoView()


def render_cart():
    box = q("#cart-items")
    if not cart:
        box.innerHTML = '<p class="empty">Your reservation is empty. Pick a product from the catalog.</p>'
    else:
        html = ""
        for pid, kg in cart.items():
            p = product(pid)
            html += (
                '<div class="cart-line"><span>%s</span><span class="qty">'
                '<button class="btn small" data-act="minus" data-id="%s" aria-label="Less %s">-</button>'
                "<span>%s kg</span>"
                '<button class="btn small" data-act="plus" data-id="%s" aria-label="More %s">+</button>'
                '</span><span>%s</span><button class="link" data-act="remove" data-id="%s">Remove</button></div>'
            ) % (p["name"], pid, p["name"], kg_text(kg), pid, p["name"], peso(p["price"] * kg), pid)
        box.innerHTML = html
    q("#cart-total").innerText = peso(cart_total())
    q("#cart-count").innerText = str(len(cart))


def render_owner():
    orders = load_orders()
    if not orders:
        q("#owner-list").innerHTML = '<p class="empty">No reservations yet.</p>'
        return
    html = ""
    for o in reversed(orders):
        actions = ""
        if o["status"] == "Pending":
            actions = (
                '<div class="actions"><button class="btn small" data-verify="%s">Verify</button>'
                '<button class="btn small ghost" data-cancel="%s">Cancel</button></div>'
            ) % (o["rtn"], o["rtn"])
        html += (
            '<div class="order"><strong>%s</strong> %s<br>%s (%s), pickup %s<br>%s, %s<br>'
            '<span class="muted">Placed %s</span>%s</div>'
        ) % (o["rtn"], badge(o["status"]), esc(o["name"]), esc(o["contact"]), esc(o["date"]),
             esc(items_text(o["items"])), peso(o["total"]), esc(o["created"]), actions)
    q("#owner-list").innerHTML = html


# ---------- events: catalog ----------
@when("click", "#category-grid")
def on_category(event):
    btn = event.target.closest("[data-cat]")
    if btn:
        show_category(btn.getAttribute("data-cat"))


@when("click", "#back-btn")
def on_back(event):
    q("#product-view").classList.add("hidden")
    q("#category-view").classList.remove("hidden")
    q("#products").scrollIntoView()


def add_to_cart(pid, kg):
    cart[pid] = cart.get(pid, 0) + kg
    render_cart()
    toast("Added %s kg %s to your reservation" % (kg_text(kg), product(pid)["name"]))


@when("click", "#product-grid")
def on_product(event):
    add = event.target.closest("[data-add]")
    opn = event.target.closest("[data-open]")
    if add:
        add_to_cart(add.getAttribute("data-add"), 1)
    elif opn:
        p = product(opn.getAttribute("data-open"))
        dlg = q("#product-dialog")
        dlg.innerHTML = (
            '<div class="dlg-head"><h3>%s</h3><button class="x" data-close="product-dialog" aria-label="Close">&times;</button></div>'
            '<div class="dlg-body">%s<p>%s</p><dl><dt>Price</dt><dd>%s per kg</dd><dt>Pack</dt><dd>%s</dd>'
            "<dt>Availability</dt><dd>%s</dd><dt>Storage</dt><dd>Keep frozen at -18°C or colder</dd></dl></div>"
            '<div class="dlg-actions"><div><label for="dlg-kg">Kilos</label>'
            '<input id="dlg-kg" type="number" min="0.5" step="0.5" value="1"></div>'
            '<button class="btn" data-add-dlg="%s">Add to reservation</button></div>'
        ) % (p["name"], photo("assets/products/%s.jpg" % p["id"], "Product photo"), p["desc"],
             peso(p["price"]), p["pack"], p["stock"], p["id"])
        dlg.showModal()


@when("click", "#product-dialog")
def on_dialog(event):
    t = event.target
    if t.closest("[data-close]"):
        q("#product-dialog").close()
        return
    btn = t.closest("[data-add-dlg]")
    if btn:
        kg = float(q("#dlg-kg").value or 0)
        if kg < 0.5:
            toast("Enter at least 0.5 kg")
            return
        add_to_cart(btn.getAttribute("data-add-dlg"), kg)
        q("#product-dialog").close()


@when("click", "#owner-dialog")
def on_owner_close(event):
    if event.target.closest("[data-close]"):
        q("#owner-dialog").close()


# ---------- events: reservation ----------
@when("click", "#cart-items")
def on_cart_change(event):
    btn = event.target.closest("[data-act]")
    if not btn:
        return
    pid, act = btn.getAttribute("data-id"), btn.getAttribute("data-act")
    if act == "plus":
        cart[pid] += 0.5
    elif act == "minus":
        cart[pid] -= 0.5
    if act == "remove" or cart[pid] <= 0:
        del cart[pid]
    render_cart()


@when("click", "#reserve-btn")
def on_reserve(event):
    name = q("#cust-name").value.strip()
    contact = q("#cust-contact").value.strip()
    date = q("#cust-date").value
    bad = False
    set_error("name", "" if name else "Enter your full name.")
    ok_phone = contact.isdigit() and len(contact) == 11 and contact.startswith("09")
    set_error("contact", "" if ok_phone else "Enter an 11-digit mobile number starting with 09.")
    set_error("date", "" if date else "Choose a pickup date.")
    if not name or not ok_phone or not date:
        return
    if not cart:
        toast("Add at least one product first")
        q("#products").scrollIntoView()
        return
    orders = load_orders()
    rtn = new_rtn(orders)
    items = [{"name": product(pid)["name"], "kg": kg} for pid, kg in cart.items()]
    orders.append({
        "rtn": rtn, "name": name, "contact": contact, "date": date,
        "items": items, "total": cart_total(), "status": "Pending",
        "created": window.Date.new().toLocaleString(),
    })
    save_orders(orders)
    cart.clear()
    render_cart()
    q("#reserve-msg").innerHTML = (
        '<div class="rtn-box">Reservation received. Save your RTN:<strong>%s</strong>'
        "The owner will verify it before pickup. Use it under Check your RTN to see the status."
        '<br><button class="btn small" data-copy="%s">Copy RTN</button></div>'
    ) % (rtn, rtn)
    toast("Reservation saved")
    if owner_unlocked:
        render_owner()


@when("click", "#reserve-msg")
def on_copy(event):
    btn = event.target.closest("[data-copy]")
    if btn:
        window.navigator.clipboard.writeText(btn.getAttribute("data-copy"))
        toast("RTN copied")


@when("click", "#track-btn")
def on_track(event):
    code = q("#track-input").value.strip().upper()
    out = q("#track-result")
    for o in load_orders():
        if o["rtn"] == code:
            note = {
                "Pending": "Waiting for the owner to verify your reservation.",
                "Verified": "Verified. Show this RTN at the shop on your pickup date.",
                "Cancelled": "This reservation was cancelled. Please contact the shop.",
            }[o["status"]]
            out.innerHTML = (
                '<div class="rtn-box"><strong>%s</strong>%s<br>%s<br>%s, %s<br>Pickup: %s<br>%s</div>'
            ) % (o["rtn"], badge(o["status"]), esc(o["name"]), esc(items_text(o["items"])),
                 peso(o["total"]), esc(o["date"]), note)
            return
    out.innerHTML = '<p class="err">No reservation found for that RTN. Check the code (format LMS-XXXXXX) and try again.</p>'


# ---------- events: owner ----------
@when("click", "#owner-open")
def on_owner_open(event):
    q("#owner-dialog").showModal()


@when("click", "#owner-btn")
def on_unlock(event):
    global owner_unlocked
    if q("#owner-pin").value == OWNER_PIN:
        owner_unlocked = True
        q("#owner-msg").innerText = ""
        render_owner()
    else:
        q("#owner-msg").innerText = "Wrong PIN. Try again."


@when("click", "#owner-list")
def on_owner_action(event):
    if not owner_unlocked:
        return
    verify = event.target.closest("[data-verify]")
    cancel = event.target.closest("[data-cancel]")
    if verify:
        code, status = verify.getAttribute("data-verify"), "Verified"
    elif cancel:
        code, status = cancel.getAttribute("data-cancel"), "Cancelled"
        if not window.confirm("Cancel reservation %s?" % code):
            return
    else:
        return
    orders = load_orders()
    for o in orders:
        if o["rtn"] == code:
            o["status"] = status
    save_orders(orders)
    render_owner()
    toast("%s marked %s" % (code, status))


# ---------- startup ----------
render_categories()
render_cart()
q("#cust-date").min = window.Date.new().toISOString()[:10]
