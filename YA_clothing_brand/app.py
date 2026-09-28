from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import sqlite3
import os
import uuid

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "ya_store.db")
UPLOADS = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED = {"jpg", "jpeg", "png", "webp"}

# CHANGE THESE BEFORE PUBLISHING
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

os.makedirs(UPLOADS, exist_ok=True)


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            description TEXT,
            sizes TEXT,
            image TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@app.route("/")
def home():
    con = db()
    products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    con.close()
    return render_template("index.html", products=products)


@app.route("/product/<int:product_id>")
def product(product_id):
    con = db()
    product = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    con.close()
    if not product:
        return "Product not found", 404
    return render_template("product.html", product=product)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Wrong username or password.")

    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    con = db()
    products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    con.close()
    return render_template("admin.html", products=products)


@app.route("/admin/add", methods=["POST"])
def add_product():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    name = request.form.get("name", "").strip()
    price = request.form.get("price", "").strip()
    description = request.form.get("description", "").strip()
    sizes = request.form.get("sizes", "").strip()
    image = request.files.get("image")

    if not name or not price or not image or image.filename == "":
        flash("Product name, price and photo are required.")
        return redirect(url_for("admin"))

    if not allowed(image.filename):
        flash("Use JPG, JPEG, PNG or WEBP images.")
        return redirect(url_for("admin"))

    ext = image.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    image.save(os.path.join(UPLOADS, secure_filename(filename)))

    con = db()
    con.execute(
        "INSERT INTO products (name, price, description, sizes, image) VALUES (?, ?, ?, ?, ?)",
        (name, price, description, sizes, filename)
    )
    con.commit()
    con.close()

    flash("Product added to YA.")
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    con = db()
    product = con.execute("SELECT image FROM products WHERE id=?", (product_id,)).fetchone()
    if product:
        image_path = os.path.join(UPLOADS, product["image"])
        if os.path.exists(image_path):
            os.remove(image_path)
        con.execute("DELETE FROM products WHERE id=?", (product_id,))
        con.commit()
    con.close()

    flash("Product deleted.")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
