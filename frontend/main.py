"""Laortealbe Meat Shop - PyScript logic (event-driven).

Events used: click (add to cart, +/-, reserve, track, unlock, verify/cancel).
Reservations are saved in the browser's localStorage under KEY.
"""
import json
import random
from pyscript import document, window, when

PRODUCTS = [
    {"id": "pork", "name": "Pork", "price": 280, "img": "assets/pork.jpg"},
    {"id": "chicken", "name": "Chicken", "price": 190, "img": "assets/chicken.jpg"},
    {"id": "tuna", "name": "Tuna", "price": 320, "img": "assets/tuna.jpg"},
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


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def product(pid):
    for p in PRODUCTS:
        if p["id"] == pid:
            return p


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
    return ", ".join("%s %skg" % (i["name"], i["kg"]) for i in items)


# ---------- rendering ----------
def render_products():
    html = ""
    for p in PRODUCTS:
        html += (
            '<article class="card"><h3>%s</h3>'
            '<div class="frame"><div class="photo" style="background-image:url(\'%s\')"></div></div>'
            '<p class="price">%s per kg</p>'
            '<button class="btn" data-add="%s">Add to reservation</button></article>'
        ) % (p["name"], p["img"], peso(p["price"]), p["id"])
    q("#product-grid").innerHTML = html


def render_cart():
    box = q("#cart-items")
    if not cart:
        box.innerHTML = '<p class="muted">Nothing here yet. Add a product above.</p>'
    else:
        html = ""
        for pid, kg in cart.items():
            p = product(pid)
            html += (
                '<div class="cart-line"><span>%s</span><span class="qty">'
                '<button class="btn small" data-act="minus" data-id="%s" aria-label="Remove 1 kg">-</button>'
                '<span>%s kg</span>'
                '<button class="btn small" data-act="plus" data-id="%s" aria-label="Add 1 kg">+</button>'
                "</span><span>%s</span></div>"
            ) % (p["name"], pid, kg, pid, peso(p["price"] * kg))
        box.innerHTML = html
    q("#cart-total").innerText = peso(cart_total())


def render_owner():
    orders = load_orders()
    if not orders:
        q("#owner-list").innerHTML = '<p class="muted">No reservations yet.</p>'
        return
    html = ""
    for o in reversed(orders):
        actions = ""
        if o["status"] == "Pending":
            actions = (
                '<div class="actions">'
                '<button class="btn small" data-verify="%s">Verify</button>'
                '<button class="btn small ghost" data-cancel="%s">Cancel</button></div>'
            ) % (o["rtn"], o["rtn"])
        html += (
            '<div class="order"><strong>%s</strong> %s<br>%s (%s) - pickup %s<br>%s - %s<br>'
            '<span class="muted">Placed %s</span>%s</div>'
        ) % (o["rtn"], badge(o["status"]), esc(o["name"]), esc(o["contact"]), esc(o["date"]),
             esc(items_text(o["items"])), peso(o["total"]), esc(o["created"]), actions)
    q("#owner-list").innerHTML = html


def set_msg(sel, text, error=False):
    el = q(sel)
    el.innerText = text
    el.className = "msg err" if error else "msg"


# ---------- events ----------
@when("click", "#product-grid")
def on_add(event):
    btn = event.target.closest("[data-add]")
    if btn:
        pid = btn.getAttribute("data-add")
        cart[pid] = cart.get(pid, 0) + 1
        render_cart()


@when("click", "#cart-items")
def on_cart_change(event):
    btn = event.target.closest("[data-act]")
    if not btn:
        return
    pid = btn.getAttribute("data-id")
    if btn.getAttribute("data-act") == "plus":
        cart[pid] += 1
    else:
        cart[pid] -= 1
        if cart[pid] <= 0:
            del cart[pid]
    render_cart()


@when("click", "#reserve-btn")
def on_reserve(event):
    name = q("#cust-name").value.strip()
    contact = q("#cust-contact").value.strip()
    date = q("#cust-date").value
    if not cart:
        set_msg("#reserve-msg", "Add at least one product first.", True)
        return
    if not name or not contact or not date:
        set_msg("#reserve-msg", "Fill in your name, mobile number and pickup date.", True)
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
    q("#reserve-msg").className = "msg"
    q("#reserve-msg").innerHTML = (
        '<span class="rtn-box">Reservation received. Save your RTN:<strong>%s</strong>'
        "The owner will verify it before pickup.</span>"
    ) % rtn
    if owner_unlocked:
        render_owner()


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
                '<div class="rtn-box"><strong>%s</strong>%s<br>%s<br>%s - %s<br>Pickup: %s<br>%s</div>'
            ) % (o["rtn"], badge(o["status"]), esc(o["name"]), esc(items_text(o["items"])),
                 peso(o["total"]), esc(o["date"]), note)
            return
    out.innerHTML = '<p class="msg err">No reservation found for that RTN. Check the code and try again.</p>'


@when("click", "#owner-btn")
def on_unlock(event):
    global owner_unlocked
    if q("#owner-pin").value == OWNER_PIN:
        owner_unlocked = True
        set_msg("#owner-msg", "Unlocked.")
        render_owner()
    else:
        set_msg("#owner-msg", "Wrong PIN.", True)


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
    else:
        return
    orders = load_orders()
    for o in orders:
        if o["rtn"] == code:
            o["status"] = status
    save_orders(orders)
    render_owner()


# ---------- startup ----------
render_products()
render_cart()
q("#cust-date").min = window.Date.new().toISOString()[:10]
