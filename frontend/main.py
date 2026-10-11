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
    {"id": "sausage", "name": "Hotdogs & Sausages"},
    {"id": "beef", "name": "Beef"},
    {"id": "fish", "name": "Fish"},
]
# Products from the price list. price None = not priced yet. Photos: assets/products/<id>.jpg
PRODUCTS = [
    {"id": "pata-1-kg", "cat": "pork", "name": "Pata", "unit": "1 kg", "price": 250},
    {"id": "giniling-1-kg", "cat": "pork", "name": "Giniling", "unit": "1 kg", "price": 290},
    {"id": "kasim-menudo-cut-1-kg", "cat": "pork", "name": "Kasim (Menudo Cut)", "unit": "1 kg", "price": 290},
    {"id": "porkchop-1-kg", "cat": "pork", "name": "Porkchop", "unit": "1 kg", "price": 290},
    {"id": "liempo-1-kg", "cat": "pork", "name": "Liempo", "unit": "1 kg", "price": 330},
    {"id": "humba-cut-1-kg", "cat": "pork", "name": "Humba Cut", "unit": "1 kg", "price": 330},
    {"id": "square-cooked-ham-225-g", "cat": "pork", "name": "Square Cooked Ham", "unit": "225 g", "price": 68},
    {"id": "bacon-regular-200-g", "cat": "pork", "name": "Bacon Regular", "unit": "200 g", "price": 105},
    {"id": "chicken-breast-1-kg", "cat": "chicken", "name": "Chicken Breast", "unit": "1 kg", "price": 290},
    {"id": "chicken-whole-1-whole", "cat": "chicken", "name": "Chicken Whole", "unit": "1 whole", "price": 185},
    {"id": "chicken-hotdog-250-g", "cat": "sausage", "name": "Chicken Hotdog", "unit": "250 g", "price": 52},
    {"id": "champ-hotdog-jumbo-250-g", "cat": "sausage", "name": "Champ Hotdog Jumbo", "unit": "250 g", "price": 45},
    {"id": "champ-hotdog-jumbo-1-kg", "cat": "sausage", "name": "Champ Hotdog Jumbo", "unit": "1 kg", "price": 160},
    {"id": "prem-hotdog-jumbo-240-g", "cat": "sausage", "name": "Prem Hotdog Jumbo", "unit": "240 g", "price": 67},
    {"id": "prem-hotdog-jumbo-500-g", "cat": "sausage", "name": "Prem Hotdog Jumbo", "unit": "500 g", "price": 139},
    {"id": "prem-hotdog-regular-jumbo-1-kg", "cat": "sausage", "name": "Prem Hotdog Regular/Jumbo", "unit": "1 kg", "price": 215},
    {"id": "chorizo-pinoy-200-g", "cat": "sausage", "name": "Chorizo Pinoy", "unit": "200 g", "price": 70},
    {"id": "longaniza-hamonada-225-g", "cat": "sausage", "name": "Longaniza Hamonada", "unit": "225 g", "price": 80},
    {"id": "hamburger-patties-225-g", "cat": "beef", "name": "Hamburger Patties", "unit": "225 g", "price": 85},
    {"id": "tuna-panga-1-kg", "cat": "fish", "name": "Tuna Panga", "unit": "1 kg", "price": None},
]
OWNER_PIN = "owner123"  # demo only - change it
KEY = "laortealbe_reservations_v2"
CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

cart = {}  # product id -> quantity (packs)
owner_unlocked = False
editing = None  # RTN of the reservation being edited
drafts = {}  # product id -> quantity typed in the popup (kept when it closes)


# ---------- helpers ----------
def q(sel):
    return document.querySelector(sel)


def peso(n):
    return "₱" + "%.2f" % n


def kg_text(kg):
    return str(int(kg)) if kg == int(kg) else str(kg)


def label(p):
    return "%s (%s)" % (p["name"], p["unit"])


def price_text(p):
    if p["price"] is None:
        return "Price coming soon"
    return "%s / %s" % (peso(p["price"]), p["unit"])


def add_btn(p):
    if p["price"] is None:
        return '<button class="btn small" disabled>Unavailable</button>'
    return '<button class="btn small" data-add="%s">Add</button>' % p["id"]


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
    return ", ".join("%s x%d (%s)" % (i["name"], i["qty"], i["unit"]) for i in items)


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
            '<div class="meta"><span class="price">%s</span>%s</div></article>'
        ) % (p["id"], p["name"], photo("assets/products/%s.jpg" % p["id"], "Product photo"),
             p["name"], price_text(p), add_btn(p))
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
                "<span>%s</span>"
                '<button class="btn small" data-act="plus" data-id="%s" aria-label="More %s">+</button>'
                '</span><span>%s</span><button class="link" data-act="remove" data-id="%s">Remove</button></div>'
            ) % (label(p), pid, p["name"], kg, pid, p["name"], peso(p["price"] * kg), pid)
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
        placed = "Placed " + o["created"] + (", edited " + o["edited"] if o.get("edited") else "")
        if o["status"] == "Pending":
            actions = (
                '<div class="actions"><button class="btn small" data-verify="%s">Verify</button>'
                '<button class="btn small ghost" data-cancel="%s">Cancel</button></div>'
            ) % (o["rtn"], o["rtn"])
        html += (
            '<div class="order"><strong>%s</strong> %s<br>%s (%s), pickup %s<br>%s, %s<br>'
            '<span class="muted">%s</span>%s</div>'
        ) % (o["rtn"], badge(o["status"]), esc(o["name"]), esc(o["contact"]), esc(o["date"]),
             esc(items_text(o["items"])), peso(o["total"]), esc(placed), actions)
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


def add_to_cart(pid, qty):
    cart[pid] = cart.get(pid, 0) + qty
    render_cart()
    toast("Added %s to your reservation" % label(product(pid)))


@when("click", "#product-grid")
def on_product(event):
    add = event.target.closest("[data-add]")
    opn = event.target.closest("[data-open]")
    if add:
        add_to_cart(add.getAttribute("data-add"), 1)
    elif opn:
        p = product(opn.getAttribute("data-open"))
        dlg = q("#product-dialog")
        dq = drafts.get(p["id"], 1)
        if p["price"] is None:
            actions = '<p class="muted">Price coming soon. This item cannot be reserved yet.</p>'
        else:
            actions = (
                '<div class="dlg-buy"><label for="dlg-qty">Quantity</label>'
                '<div class="stepper"><button class="btn ghost" data-step="-1" aria-label="Less">-</button>'
                '<input id="dlg-qty" type="number" min="1" step="1" value="%d" data-price="%s" data-pid="%s">'
                '<button class="btn ghost" data-step="1" aria-label="More">+</button></div>'
                '<p class="dlg-total">Total <strong id="dlg-total">%s</strong>'
                '<span id="dlg-calc" class="muted">%d x %s</span></p>'
                '<button class="btn" data-add-dlg="%s">Add to reservation</button></div>'
            ) % (dq, p["price"], p["id"], peso(p["price"] * dq), dq, peso(p["price"]), p["id"])
        dlg.innerHTML = (
            '<div class="dlg-inner"><div class="dlg-head"><h3>%s</h3><button class="x" data-close="product-dialog" aria-label="Close">&times;</button></div>'
            '<div class="dlg-body">%s<dl><dt>Price</dt><dd>%s</dd><dt>Sold as</dt><dd>%s</dd>'
            "<dt>Storage</dt><dd>Keep frozen at -18°C or colder</dd></dl></div>%s</div>"
        ) % (p["name"], photo("assets/products/%s.jpg" % p["id"], "Product photo"),
             price_text(p), p["unit"], actions)
        dlg.showModal()


@when("click", "#product-dialog")
def on_dialog(event):
    t = event.target
    if t.id == "product-dialog":  # click on the dark area outside the popup
        q("#product-dialog").close()
        return
    if t.closest("[data-close]"):
        q("#product-dialog").close()
        return
    step = t.closest("[data-step]")
    if step:
        qty = int(float(q("#dlg-qty").value or 0)) + int(step.getAttribute("data-step"))
        q("#dlg-qty").value = str(max(1, qty))
        update_total()
        return
    btn = t.closest("[data-add-dlg]")
    if btn:
        qty = int(float(q("#dlg-qty").value or 0))
        if qty < 1:
            toast("Enter a quantity of at least 1")
            return
        add_to_cart(btn.getAttribute("data-add-dlg"), qty)
        drafts.pop(btn.getAttribute("data-add-dlg"), None)
        q("#product-dialog").close()


def update_total():
    box = q("#dlg-qty")
    qty = max(0, int(float(box.value or 0)))
    price = float(box.getAttribute("data-price"))
    if qty >= 1:
        drafts[box.getAttribute("data-pid")] = qty
    q("#dlg-total").innerText = peso(price * qty)
    q("#dlg-calc").innerText = "%d x %s" % (qty, peso(price))


@when("input", "#product-dialog")
def on_qty_typed(event):
    if event.target.id == "dlg-qty":
        update_total()


@when("click", "#owner-dialog")
def on_owner_close(event):
    if event.target.closest("[data-close]"):
        q("#owner-dialog").close()


def clear_form():
    for f in ("name", "contact", "date"):
        q("#cust-" + f).value = ""
        set_error(f, "")


def stop_editing():
    global editing
    editing = None
    q("#edit-banner").classList.add("hidden")
    q("#reserve-btn").innerText = "Reserve now"


# ---------- events: reservation ----------
@when("click", "#cart-items")
def on_cart_change(event):
    btn = event.target.closest("[data-act]")
    if not btn:
        return
    pid, act = btn.getAttribute("data-id"), btn.getAttribute("data-act")
    if act == "plus":
        cart[pid] += 1
    elif act == "minus":
        cart[pid] -= 1
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
    items = [{"id": pid, "name": product(pid)["name"], "unit": product(pid)["unit"], "qty": qty}
             for pid, qty in cart.items()]
    now = window.Date.new().toLocaleString()
    if editing:
        rtn = editing
        for o in orders:
            if o["rtn"] == rtn:
                if o["status"] != "Pending":
                    toast("This reservation is already %s and can no longer be edited" % o["status"].lower())
                    stop_editing()
                    return
                o["name"], o["contact"], o["date"] = name, contact, date
                o["items"], o["total"], o["edited"] = items, cart_total(), now
        headline = "Reservation updated. Your RTN stays the same:"
    else:
        rtn = new_rtn(orders)
        orders.append({
            "rtn": rtn, "name": name, "contact": contact, "date": date,
            "items": items, "total": cart_total(), "status": "Pending", "created": now,
        })
        headline = "Reservation received. Save your RTN:"
    save_orders(orders)
    stop_editing()
    cart.clear()
    render_cart()
    clear_form()
    q("#reserve-msg").innerHTML = (
        '<div class="rtn-box">%s<strong>%s</strong>'
        "The owner will verify it before pickup. Use it under Check your RTN to see the status."
        '<br><button class="btn small" data-copy="%s">Copy RTN</button></div>'
    ) % (headline, rtn, rtn)
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
                "Verified": "Verified. Show this RTN at the shop on your pickup date. It can no longer be edited online.",
                "Cancelled": "This reservation was cancelled. Please contact the shop.",
            }[o["status"]]
            extra = ""
            if o["status"] == "Pending":
                extra = '<br><button class="btn small" data-edit="%s">Edit reservation</button>' % o["rtn"]
            out.innerHTML = (
                '<div class="rtn-box"><strong>%s</strong>%s<br>%s<br>%s, %s<br>Pickup: %s<br>%s%s</div>'
            ) % (o["rtn"], badge(o["status"]), esc(o["name"]), esc(items_text(o["items"])),
                 peso(o["total"]), esc(o["date"]), note, extra)
            return
    out.innerHTML = '<p class="err">No reservation found for that RTN. Check the code (format LMS-XXXXXX) and try again.</p>'


@when("click", "#track-result")
def on_edit_click(event):
    global editing
    btn = event.target.closest("[data-edit]")
    if not btn:
        return
    code = btn.getAttribute("data-edit")
    for o in load_orders():
        if o["rtn"] == code:
            if o["status"] != "Pending":
                toast("Only pending reservations can be edited")
                return
            cart.clear()
            for i in o["items"]:
                pid = i.get("id")
                if not pid:  # older saved reservations have no id
                    for p in PRODUCTS:
                        if p["name"] == i["name"] and p["unit"] == i["unit"]:
                            pid = p["id"]
                if pid:
                    cart[pid] = i["qty"]
            editing = code
            q("#cust-name").value = o["name"]
            q("#cust-contact").value = o["contact"]
            q("#cust-date").value = o["date"]
            q("#edit-rtn").innerText = code
            q("#edit-banner").classList.remove("hidden")
            q("#reserve-btn").innerText = "Save changes"
            q("#reserve-msg").innerHTML = ""
            render_cart()
            q("#reservation").scrollIntoView()
            toast("Editing %s. Change your items or details, then save." % code)
            return


@when("click", "#edit-cancel")
def on_edit_cancel(event):
    stop_editing()
    cart.clear()
    render_cart()
    clear_form()
    toast("Editing cancelled. Your reservation was not changed.")


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
