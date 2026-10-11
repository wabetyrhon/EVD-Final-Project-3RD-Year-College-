"""Frozen meat shop - PyScript frontend (event-driven) for the Flask API.

API used:
  GET  /api/products              -> [{product_id, name, unit, price}]
  POST /api/reservations          -> {message, reservation_id}  (reservation_id is the RTN)
  GET  /api/reservations/<id>     -> reservation details
Events: click (categories, products, cart, reserve, confirm, track), input (quantity box).
"""
import json
from pyscript import document, window, when, fetch
from pyscript.ffi import create_proxy

API = ""  # same origin as the Flask app
STATIC = "/"

CATEGORY_NAMES = {"pork": "Pork", "chicken": "Chicken", "sausage": "Hotdogs & Sausages",
                  "beef": "Beef", "fish": "Fish", "other": "Other products"}
CATEGORY_ORDER = ["pork", "chicken", "sausage", "beef", "fish", "other"]
# The API has no category field, so a product's category is guessed from its name.
# Checked in order, so "Chicken Hotdog" lands in sausage before chicken.
KEYWORDS = [
    ("sausage", ("hotdog", "chorizo", "longaniza", "sausage")),
    ("chicken", ("chicken",)),
    ("fish", ("tuna", "fish", "panga", "bangus", "tilapia", "salmon")),
    ("beef", ("beef", "hamburger", "patties")),
    ("pork", ("pork", "pata", "giniling", "kasim", "liempo", "humba", "ham", "bacon")),
]

products = []  # loaded from /api/products
cart = {}  # product id (text) -> quantity
details = {}  # customer details waiting for confirmation
drafts = {}  # product id -> quantity typed in the popup (kept when it closes)


# ---------- helpers ----------
def q(sel):
    return document.querySelector(sel)


def peso(n):
    return "₱" + "%.2f" % n


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def category_of(name):
    low = name.lower()
    for cat, words in KEYWORDS:
        for w in words:
            if w in low:
                return cat
    return "other"


def product(pid):
    for p in products:
        if p["id"] == pid:
            return p


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


def photo(src, text):
    return '<div class="photo">%s<img src="%s" alt="" onerror="this.remove()"></div>' % (text, src)


def toast(text):
    t = q("#toast")
    t.innerText = text
    t.classList.add("show")
    window.setTimeout(create_proxy(lambda: t.classList.remove("show")), 2400)


def cart_total():
    return sum(product(pid)["price"] * qty for pid, qty in cart.items())


def cart_items():
    return [{"id": pid, "qty": qty} for pid, qty in cart.items()]


def set_error(field, text):
    q("#err-" + field).innerText = text
    q("#cust-" + field).setAttribute("aria-invalid", "true" if text else "false")


def clear_form():
    for f in ("name", "email", "contact", "date"):
        q("#cust-" + f).value = ""
        set_error(f, "")


def summary_html(items, total, name, email, contact, date):
    rows = ""
    for i in items:
        p = product(i["id"])
        rows += '<div class="cart-line"><span>%s</span><span>x%d</span><span>%s</span></div>' % (
            esc(label(p)), i["qty"], peso(p["price"] * i["qty"]))
    return (
        '<div class="sum">%s<p class="total">Total <span>%s</span></p>'
        '<dl class="facts-lite"><dt>Name</dt><dd>%s</dd><dt>Email</dt><dd>%s</dd>'
        "<dt>Mobile</dt><dd>%s</dd><dt>Pickup date</dt><dd>%s</dd></dl></div>"
    ) % (rows, peso(total), esc(name), esc(email), esc(contact), esc(date))


# ---------- loading products from the API ----------
async def load_products():
    try:
        res = await fetch(API + "/api/products")
        if not res.ok:
            raise ValueError("bad status")
        data = await res.json()
    except Exception:
        q("#category-grid").innerHTML = (
            '<p class="empty">Could not load products. Check your connection, then refresh the page.</p>')
        return
    for d in data:
        products.append({
            "id": str(d["product_id"]), "pid": d["product_id"], "name": d["name"],
            "unit": d["unit"], "price": d["price"], "cat": category_of(d["name"]),
            "img_url": d.get("img_url"),
        })
    render_categories()


# ---------- rendering ----------
def render_categories():
    html = ""
    for cid in CATEGORY_ORDER:
        n = len([p for p in products if p["cat"] == cid])
        if n:
            html += (
                '<button class="cat-card" data-cat="%s">%s<h3>%s</h3><p>%d products</p></button>'
            ) % (cid, photo(STATIC + "images/%s.jpg" % cid, "Category photo"), CATEGORY_NAMES[cid], n)
    q("#category-grid").innerHTML = html or '<p class="empty">No products yet. Please check back soon.</p>'


def show_category(cid):
    html = ""
    for p in [p for p in products if p["cat"] == cid]:
        html += (
            '<article class="pcard"><button class="pcard-main" data-open="%s" aria-label="View details for %s">'
            "%s<h3>%s</h3></button>"
            '<div class="meta"><span class="price">%s</span>%s</div></article>'
        ) % (p["id"], esc(p["name"]), photo(p.get("img_url") or "", "Product photo"),
             esc(p["name"]), price_text(p), add_btn(p))
    q("#product-grid").innerHTML = html
    q("#product-title").innerText = CATEGORY_NAMES[cid]
    q("#category-view").classList.add("hidden")
    q("#product-view").classList.remove("hidden")
    q("#products").scrollIntoView()


def render_cart():
    box = q("#cart-items")
    if not cart:
        box.innerHTML = '<p class="empty">Your reservation is empty. Pick a product from the catalog.</p>'
    else:
        html = ""
        for pid, qty in cart.items():
            p = product(pid)
            html += (
                '<div class="cart-line"><span>%s</span><span class="qty">'
                '<button class="btn small" data-act="minus" data-id="%s" aria-label="Less %s">-</button>'
                "<span>%s</span>"
                '<button class="btn small" data-act="plus" data-id="%s" aria-label="More %s">+</button>'
                '</span><span>%s</span>'
                '<button class="btn small ghost" data-act="remove" data-id="%s" aria-label="Remove %s">'
                '<span class="rm-text">Remove</span><span class="rm-x">&times;</span></button></div>'
            ) % (esc(label(p)), pid, esc(p["name"]), qty, pid, esc(p["name"]), peso(p["price"] * qty), pid, esc(p["name"]))
        box.innerHTML = html
    q("#cart-total").innerText = peso(cart_total())
    q("#cart-count").innerText = str(len(cart))


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
        ) % (esc(p["name"]), photo(p.get("img_url") or "", "Product photo"),
             price_text(p), esc(p["unit"]), actions)
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
    email = q("#cust-email").value.strip()
    contact = q("#cust-contact").value.strip()
    date = q("#cust-date").value
    ok_email = "@" in email and "." in email.split("@")[-1] and " " not in email
    ok_phone = contact.isdigit() and len(contact) == 11 and contact.startswith("09")
    set_error("name", "" if name else "Enter your full name.")
    set_error("email", "" if ok_email else "Enter a valid email, like name@example.com.")
    set_error("contact", "" if ok_phone else "Enter an 11-digit mobile number starting with 09.")
    set_error("date", "" if date else "Choose a pickup date.")
    if not name or not ok_email or not ok_phone or not date:
        return
    if not cart:
        toast("Add at least one product first")
        q("#products").scrollIntoView()
        return
    show_confirm(name, email, contact, date)


def show_confirm(name, email, contact, date):
    global details
    details = {"name": name, "email": email, "contact": contact, "date": date}
    dlg = q("#confirm-dialog")
    dlg.innerHTML = (
        '<div class="dlg-inner"><div class="dlg-head"><h3>Review your reservation</h3>'
        '<button class="x" data-back aria-label="Close">&times;</button></div>%s'
        '<p class="hint">Please check everything. You pay at the shop.</p>'
        '<p id="confirm-error" class="err" role="alert"></p>'
        '<div class="dlg-foot"><button class="btn ghost" data-back>Go back</button>'
        '<button class="btn" data-confirm>Confirm reservation</button></div></div>'
    ) % summary_html(cart_items(), cart_total(), name, email, contact, date)
    dlg.showModal()


def fail(message, btn):
    q("#confirm-error").innerText = message
    btn.disabled = False
    btn.innerText = "Confirm reservation"


@when("click", "#confirm-dialog")
async def on_confirm(event):
    t = event.target
    dlg = q("#confirm-dialog")
    if t.id == "confirm-dialog" or t.closest("[data-back]") or t.closest("[data-done]"):
        dlg.close()  # outside click, Go back, x or Done: nothing is lost
        return
    copy = t.closest("[data-copy]")
    if copy:
        window.navigator.clipboard.writeText(copy.getAttribute("data-copy"))
        toast("RTN copied")
        return
    btn = t.closest("[data-confirm]")
    if not btn:
        return

    btn.disabled = True
    btn.innerText = "Saving..."
    q("#confirm-error").innerText = ""
    d = details
    items = cart_items()
    total = cart_total()
    body = {
        "customer_name": d["name"], "customer_email": d["email"], "customer_phone": d["contact"],
        "pickup_date": d["date"],
        "items": [{"product_id": product(i["id"])["pid"], "quantity": i["qty"]} for i in items],
    }
    try:
        res = await fetch(API + "/api/reservations", method="POST",
                          headers={"Content-Type": "application/json"}, body=json.dumps(body))
    except Exception:
        fail("Could not reach the shop. Check your connection and try again.", btn)
        return
    try:
        data = await res.json()
    except Exception:
        data = {}
    if not res.ok:
        fail(data.get("error", "The shop could not save your reservation. Please try again."), btn)
        return

    rtn = data["reservation_id"]
    dlg.innerHTML = (
        '<div class="dlg-inner"><div class="dlg-head"><h3>Reservation received</h3>'
        '<button class="x" data-done aria-label="Close">&times;</button></div>'
        '<div class="rtn-box">Save your RTN<strong>%s</strong>'
        "Show it at the shop. The owner will verify it before pickup."
        '<br><button class="btn small" data-copy="%s">Copy RTN</button></div>%s'
        '<div class="dlg-foot"><button class="btn" data-done>Done</button></div></div>'
    ) % (esc(rtn), esc(rtn), summary_html(items, total, d["name"], d["email"], d["contact"], d["date"]))
    cart.clear()
    render_cart()
    clear_form()
    q("#reserve-msg").innerHTML = (
        '<div class="rtn-box">Reservation received. Your RTN:<strong>%s</strong>'
        "Use it under Check your RTN to look up your reservation."
        '<br><button class="btn small" data-copy="%s">Copy RTN</button></div>'
    ) % (esc(rtn), esc(rtn))
    toast("Reservation saved")


@when("click", "#reserve-msg")
def on_copy(event):
    btn = event.target.closest("[data-copy]")
    if btn:
        window.navigator.clipboard.writeText(btn.getAttribute("data-copy"))
        toast("RTN copied")


@when("click", "#track-btn")
async def on_track(event):
    code = q("#track-input").value.strip()
    out = q("#track-result")
    if not code:
        out.innerHTML = '<p class="err">Enter your RTN first.</p>'
        return
    out.innerHTML = '<p class="muted">Checking...</p>'
    try:
        res = await fetch(API + "/api/reservations/" + window.encodeURIComponent(code))
    except Exception:
        out.innerHTML = '<p class="err">Could not reach the shop. Check your connection and try again.</p>'
        return
    if not res.ok:
        out.innerHTML = '<p class="err">No reservation found for that RTN. Check the code and try again.</p>'
        return
    data = await res.json()
    lines = []
    total = 0
    for it in data["items"]:
        p = product(str(it["product_id"]))
        if p:
            lines.append("%s x%d" % (label(p), it["quantity"]))
            if p["price"] is not None:
                total += p["price"] * it["quantity"]
        else:
            lines.append("Product #%s x%d" % (it["product_id"], it["quantity"]))
    placed = (data.get("created_at") or "")[:16].replace("T", " ")
    out.innerHTML = (
        '<div class="rtn-box"><strong>%s</strong>%s<br>%s<br>%s<br>Pickup: %s<br>'
        '<span class="muted">Placed %s</span><br>'
        "Show this RTN at the shop on your pickup date. The owner will verify it.</div>"
    ) % (esc(data["reservation_id"]), esc(data["customer_name"]), esc(", ".join(lines)),
         "Total " + peso(total), esc(data.get("pickup_date") or "Not set"), esc(placed))


@when("click", "#cust-date")
def on_date_click(event):
    try:
        q("#cust-date").showPicker()  # open the calendar when the field is clicked
    except Exception:
        pass


# ---------- startup ----------
q("#cust-date").min = window.Date.new().toISOString()[:10]
render_cart()
await load_products()
