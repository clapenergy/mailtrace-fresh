from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from markupsafe import Markup
import os
import pandas as pd
from mailtrace_matcher import run_matcher

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        mail_file = request.files.get("mail_csv")
        crm_file = request.files.get("crm_csv")
        if not mail_file or not crm_file:
            flash("Please upload both Mail and CRM CSV files.", "error")
            return redirect(url_for("index"))
        mail_path = os.path.join(app.config["UPLOAD_FOLDER"], "mail.csv")
        crm_path = os.path.join(app.config["UPLOAD_FOLDER"], "crm.csv")
        mail_file.save(mail_path)
        crm_file.save(crm_path)
        results, kpis = run_matcher(mail_path, crm_path)
        out_csv = os.path.join(app.config["UPLOAD_FOLDER"], "results.csv")
        results.to_csv(out_csv, index=False)
        session["results_path"] = out_csv
        session["kpis"] = kpis
        return redirect(url_for("results"))
    return render_template("index.html")

@app.route("/results")
def results():
    results_path = session.get("results_path")
    kpis = session.get("kpis")
    if not results_path or not os.path.exists(results_path):
        flash("No results found. Please upload files again.", "error")
        return redirect(url_for("index"))
    df = pd.read_csv(results_path)
    table_html = Markup(df.to_html(classes="table table-striped", index=False))
    return render_template("result.html", table=table_html, kpis=kpis)

@app.route("/download")
def download():
    results_path = session.get("results_path")
    if results_path and os.path.exists(results_path):
        return send_file(results_path, as_attachment=True)
    flash("No results available to download.", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
