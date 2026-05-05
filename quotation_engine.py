from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib
import hmac
import json
import smtplib
from email.message import EmailMessage

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSET_DIR = BASE_DIR / "assets"
ASSET_DIR.mkdir(exist_ok=True)

DEFAULT_TERMS = """1. Prices are in AED and exclusive of any additional civil works unless mentioned.
2. Delivery timeline and installation schedule are subject to final site readiness confirmation.
3. Quotation validity is as mentioned above.
4. Warranty, payment terms, exclusions and scope shall be confirmed in the final commercial offer."""

@dataclass
class QuoteRequest:
    customer_name: str
    customer_company: str
    customer_email: str
    customer_phone: str
    project_name: str
    bundle_type: str
    size: str
    quantity: int
    discount_pct: float = 0.0
    vat_pct: float = 5.0
    validity_days: int = 30
    notes: str = ""
    margin_pct: float = 0.0
    prepared_by: str = ""
    additional_services: List[Dict] = field(default_factory=list)

class DataRepository:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.bundle_catalog_path = self.data_dir / "bundle_catalog.csv"
        self.bundle_components_path = self.data_dir / "bundle_components.csv"
        self.pricing_path = self.data_dir / "pricing.csv"
        self.users_path = self.data_dir / "users.csv"
        self.settings_path = self.data_dir / "settings.json"
        self.quote_log_path = self.data_dir / "quote_log.csv"

    def load_bundle_catalog(self) -> pd.DataFrame:
        return pd.read_csv(self.bundle_catalog_path).fillna("")

    def load_bundle_components(self) -> pd.DataFrame:
        return pd.read_csv(self.bundle_components_path).fillna("")

    def load_pricing(self) -> pd.DataFrame:
        return pd.read_csv(self.pricing_path).fillna("")

    def save_bundle_catalog(self, df: pd.DataFrame) -> None:
        df.to_csv(self.bundle_catalog_path, index=False)

    def save_bundle_components(self, df: pd.DataFrame) -> None:
        df.to_csv(self.bundle_components_path, index=False)

    def save_pricing(self, df: pd.DataFrame) -> None:
        df.to_csv(self.pricing_path, index=False)

    def ensure_default_files(self) -> None:
        if not self.users_path.exists():
            users = pd.DataFrame([
                {"username":"admin", "password_hash": hash_password("admin123"), "role":"Admin", "full_name":"ENEQ Admin", "email":""},
                {"username":"sales", "password_hash": hash_password("sales123"), "role":"Sales", "full_name":"Sales User", "email":""},
                {"username":"viewer", "password_hash": hash_password("viewer123"), "role":"Viewer", "full_name":"Viewer User", "email":""},
            ])
            users.to_csv(self.users_path, index=False)
        if not self.settings_path.exists():
            self.save_settings(default_settings())
        if not self.quote_log_path.exists():
            pd.DataFrame(columns=["quote_number","quote_date","customer_company","customer_name","customer_email","project_name","bundle_type","quantity","subtotal_aed","margin_pct","discount_pct","grand_total_aed","prepared_by"]).to_csv(self.quote_log_path, index=False)

    def load_users(self) -> pd.DataFrame:
        self.ensure_default_files()
        return pd.read_csv(self.users_path).fillna("")

    def save_users(self, df: pd.DataFrame) -> None:
        df.to_csv(self.users_path, index=False)

    def load_settings(self) -> Dict:
        self.ensure_default_files()
        with open(self.settings_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_settings(self, settings: Dict) -> None:
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    def append_quote_log(self, summary: Dict) -> None:
        self.ensure_default_files()
        row = {k: summary.get(k, "") for k in ["quote_number","quote_date","customer_company","customer_name","customer_email","project_name","bundle_type","quantity","subtotal_aed","margin_pct","discount_pct","grand_total_aed","prepared_by"]}
        existing = pd.read_csv(self.quote_log_path) if self.quote_log_path.exists() else pd.DataFrame()
        pd.concat([existing, pd.DataFrame([row])], ignore_index=True).to_csv(self.quote_log_path, index=False)

    def load_quote_log(self) -> pd.DataFrame:
        self.ensure_default_files()
        return pd.read_csv(self.quote_log_path).fillna("")

def default_settings() -> Dict:
    return {
        "company_name": "ENEQ Solutions LLC",
        "company_address": "Dubai, United Arab Emirates",
        "company_phone": "",
        "company_email": "",
        "company_website": "www.eneqsolutions.com",
        "logo_path": "",
        "primary_color": "#0F3D91",
        "secondary_color": "#0B5FB3",
        "vat_pct": 5.0,
        "default_margin_pct": 20.0,
        "max_sales_discount_pct": 5.0,
        "terms": DEFAULT_TERMS,
        "email_sender_name": "ENEQ Solutions",
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "smtp_use_tls": True,
    }

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def authenticate(repo: DataRepository, username: str, password: str) -> Optional[Dict]:
    users = repo.load_users()
    match = users[users["username"].astype(str).str.lower() == username.lower().strip()]
    if match.empty:
        return None
    row = match.iloc[0].to_dict()
    if hmac.compare_digest(str(row.get("password_hash", "")), hash_password(password)):
        return row
    return None

def generate_quote_number() -> str:
    return f"ENEQ-Q-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def get_bundle_options(repo: DataRepository) -> List[str]:
    catalog = repo.load_bundle_catalog()
    active_col = catalog.get("active", True)
    active = catalog[active_col.astype(str).str.lower().isin(["true", "1", "yes", "y"])] if hasattr(active_col, "astype") else catalog
    return sorted(active["bundle_type"].dropna().unique().tolist())

def get_bundle_details(repo: DataRepository, bundle_type: str) -> Dict[str, str]:
    catalog = repo.load_bundle_catalog()
    match = catalog[catalog["bundle_type"] == bundle_type]
    if match.empty:
        return {"bundle_name": bundle_type, "size": "", "mode": "", "family": ""}
    row = match.iloc[0]
    return {"bundle_name": str(row.get("bundle_name", bundle_type)), "size": str(row.get("size", "")), "mode": str(row.get("mode", "")), "family": str(row.get("family", ""))}

def calculate_quote(repo: DataRepository, request: QuoteRequest) -> Tuple[Dict, pd.DataFrame]:
    components = repo.load_bundle_components()
    bundle_rows = components[components["bundle_type"] == request.bundle_type].copy()
    if bundle_rows.empty:
        raise ValueError(f"No components found for bundle type: {request.bundle_type}")

    bundle_rows["quantity_per_bundle"] = pd.to_numeric(bundle_rows["quantity"], errors="coerce").fillna(0)
    bundle_rows["base_unit_price_aed"] = pd.to_numeric(bundle_rows["unit_price_aed"], errors="coerce").fillna(0)
    bundle_rows["margin_pct"] = float(request.margin_pct)
    bundle_rows["selling_unit_price_aed"] = bundle_rows["base_unit_price_aed"] * (1 + float(request.margin_pct) / 100.0)
    bundle_rows["requested_quantity"] = int(request.quantity)
    bundle_rows["total_quantity"] = bundle_rows["quantity_per_bundle"] * int(request.quantity)
    bundle_rows["total_line_amount_aed"] = bundle_rows["total_quantity"] * bundle_rows["selling_unit_price_aed"]

    table_df = bundle_rows[["part_no", "description", "category", "quantity_per_bundle", "requested_quantity", "total_quantity", "selling_unit_price_aed", "total_line_amount_aed"]].rename(columns={
        "part_no": "Part No", "description": "Description", "category": "Category", "quantity_per_bundle": "Qty / Bundle", "requested_quantity": "No. of Bundles", "total_quantity": "Total Qty", "selling_unit_price_aed": "Unit Price (AED)", "total_line_amount_aed": "Line Total (AED)",
    })

    additional_rows = []
    for item in request.additional_services or []:
        service_name = str(item.get("name", "")).strip()
        unit_price = float(item.get("unit_price", 0) or 0)
        service_qty = int(item.get("qty", 0) or 0)
        if service_name and unit_price >= 0 and service_qty > 0:
            additional_rows.append({
                "Part No": "SERVICE",
                "Description": service_name,
                "Category": "Additional Services",
                "Qty / Bundle": "-",
                "No. of Bundles": "-",
                "Total Qty": service_qty,
                "Unit Price (AED)": unit_price,
                "Line Total (AED)": unit_price * service_qty,
            })

    additional_df = pd.DataFrame(additional_rows, columns=table_df.columns) if additional_rows else pd.DataFrame(columns=table_df.columns)
    if not additional_df.empty:
        table_df = pd.concat([table_df, additional_df], ignore_index=True)

    bundle_total = float(bundle_rows["total_line_amount_aed"].sum())
    additional_total = float(additional_df["Line Total (AED)"].sum()) if not additional_df.empty else 0.0
    subtotal = bundle_total + additional_total
    discount_amount = subtotal * (request.discount_pct / 100.0)
    after_discount = subtotal - discount_amount
    vat_amount = after_discount * (request.vat_pct / 100.0)
    grand_total = after_discount + vat_amount

    details = get_bundle_details(repo, request.bundle_type)
    summary = {
        "quote_number": generate_quote_number(),
        "quote_date": datetime.now().strftime("%d-%b-%Y"),
        "valid_until": (datetime.now() + pd.Timedelta(days=request.validity_days)).strftime("%d-%b-%Y"),
        "bundle_type": request.bundle_type,
        "size": request.size or details.get("size", ""),
        "mode": details.get("mode", ""),
        "quantity": int(request.quantity),
        "bundle_total_aed": round(bundle_total, 2),
        "additional_services_total_aed": round(additional_total, 2),
        "subtotal_aed": round(subtotal, 2),
        "margin_pct": request.margin_pct,
        "discount_pct": request.discount_pct,
        "discount_amount_aed": round(discount_amount, 2),
        "vat_pct": request.vat_pct,
        "vat_amount_aed": round(vat_amount, 2),
        "grand_total_aed": round(grand_total, 2),
        "customer_name": request.customer_name,
        "customer_company": request.customer_company,
        "customer_email": request.customer_email,
        "customer_phone": request.customer_phone,
        "project_name": request.project_name,
        "notes": request.notes,
        "prepared_by": request.prepared_by,
    }

    return summary, table_df

def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def _p(text: str, style) -> Paragraph:
    return Paragraph(str(text).replace("\n", "<br/>"), style)

def build_quote_pdf(summary: Dict, table_df: pd.DataFrame, settings: Optional[Dict] = None) -> bytes:
    settings = settings or default_settings()
    primary = colors.HexColor(settings.get("primary_color", "#0F3D91"))
    light = colors.HexColor("#EAF2FF")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], fontSize=17, textColor=primary, leading=20, alignment=2))
    story = []

    logo_path = settings.get("logo_path", "")
    logo_cell = ""
    if logo_path and Path(logo_path).exists():
        logo_cell = Image(logo_path, width=36*mm, height=18*mm, kind="proportional")
    header_right = _p(f"<b>{settings.get('company_name','ENEQ Solutions')}</b><br/>{settings.get('company_address','')}<br/>{settings.get('company_email','')} {settings.get('company_phone','')}<br/>{settings.get('company_website','')}", styles["Small"])
    header = Table([[logo_cell, header_right]], colWidths=[55*mm, 125*mm])
    header.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("ALIGN", (1,0), (1,0), "RIGHT")]))
    story.extend([header, Spacer(1, 5), Table([[""]], colWidths=[180*mm], rowHeights=[1.2*mm], style=TableStyle([("BACKGROUND", (0,0), (-1,-1), primary)])), Spacer(1, 8)])

    story.append(Paragraph("COMMERCIAL QUOTATION", styles["BrandTitle"]))
    story.append(Spacer(1, 8))

    meta_rows = [
        ["Quote No.", summary["quote_number"], "Date", summary["quote_date"]],
        ["Customer", summary["customer_name"] or "-", "Company", summary["customer_company"] or "-"],
        ["Email", summary["customer_email"] or "-", "Phone", summary["customer_phone"] or "-"],
        ["Project", summary["project_name"] or "-", "Valid Until", summary["valid_until"]],
        ["Bundle", summary["bundle_type"], "Size", summary["size"] or "-"],
        ["Quantity", str(summary["quantity"]), "Prepared By", summary.get("prepared_by", "-") or "-"],
    ]
    meta_table = Table(meta_rows, colWidths=[24*mm, 62*mm, 25*mm, 69*mm])
    meta_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), light), ("BOX", (0,0), (-1,-1), 0.5, colors.grey), ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey), ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8.5), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5)]))
    story.extend([meta_table, Spacer(1, 8)])

    quote_table = table_df.copy().round(2)
    table_data = [quote_table.columns.tolist()] + quote_table.values.tolist()
    item_table = Table(table_data, repeatRows=1, colWidths=[22*mm, 54*mm, 21*mm, 17*mm, 20*mm, 17*mm, 23*mm, 24*mm])
    item_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), primary), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 7.4), ("GRID", (0,0), (-1,-1), 0.25, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP"), ("ALIGN", (3,1), (-1,-1), "RIGHT")]))
    story.extend([item_table, Spacer(1, 8)])

    totals_rows = []
    if float(summary.get("additional_services_total_aed", 0) or 0) > 0:
        totals_rows.extend([
            ["Bundle Total (AED)", f"{summary.get('bundle_total_aed', 0):,.2f}"],
            ["Additional Services (AED)", f"{summary.get('additional_services_total_aed', 0):,.2f}"],
        ])
    totals_rows.extend([["Subtotal (AED)", f"{summary['subtotal_aed']:,.2f}"], [f"Discount ({summary['discount_pct']:.2f}%)", f"{summary['discount_amount_aed']:,.2f}"], [f"VAT ({summary['vat_pct']:.2f}%)", f"{summary['vat_amount_aed']:,.2f}"], ["Grand Total (AED)", f"{summary['grand_total_aed']:,.2f}"]])
    totals_table = Table(totals_rows, colWidths=[54*mm, 38*mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 0.5, colors.grey), ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"), ("BACKGROUND", (0,-1), (-1,-1), light), ("ALIGN", (1,0), (1,-1), "RIGHT"), ("FONTSIZE", (0,0), (-1,-1), 9)]))
    story.extend([totals_table, Spacer(1, 8)])

    notes = summary.get("notes", "") or settings.get("terms", DEFAULT_TERMS)
    story.append(_p(f"<b>Commercial Terms / Notes:</b><br/>{notes}", styles["Small"]))
    doc.build(story)
    return buffer.getvalue()

def send_quote_email(settings: Dict, to_email: str, subject: str, body: str, pdf_bytes: bytes, filename: str, cc: str = "") -> None:
    if not to_email:
        raise ValueError("Customer email is required.")
    if not settings.get("smtp_host") or not settings.get("smtp_username") or not settings.get("smtp_password"):
        raise ValueError("SMTP settings are missing. Configure them in Admin > Company & Email Settings.")
    msg = EmailMessage()
    sender_name = settings.get("email_sender_name", "ENEQ Solutions")
    msg["From"] = f"{sender_name} <{settings.get('smtp_username')}>"
    msg["To"] = to_email
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg.set_content(body)
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)
    recipients = [to_email] + ([x.strip() for x in cc.split(",") if x.strip()] if cc else [])
    with smtplib.SMTP(settings.get("smtp_host"), int(settings.get("smtp_port", 587))) as server:
        if settings.get("smtp_use_tls", True):
            server.starttls()
        server.login(settings.get("smtp_username"), settings.get("smtp_password"))
        server.send_message(msg, to_addrs=recipients)
