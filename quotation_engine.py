from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib
import hmac
import json
import os
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
    quote_number: str = ""
    version: str = "1.0"
    discount_pct: float = 0.0
    vat_pct: float = 5.0
    validity_days: int = 30
    notes: str = ""
    margin_pct: float = 0.0
    prepared_by: str = ""
    bundle_type: str = ""  # Legacy single bundle support
    size: str = ""  # Legacy support
    quantity: int = 1  # Legacy support
    selected_bundles: List[Dict] = field(default_factory=list)  # New: List of {"bundle_type": str, "quantity": int, "components": List[Dict]}
    additional_services: List[Dict] = field(default_factory=list)
    attachments: List[Dict] = field(default_factory=list)

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
            # Generate secure default passwords - CHANGE THESE IMMEDIATELY IN PRODUCTION
            users = pd.DataFrame([
                {"username":"admin", "password_hash": hash_password("Adm!n2024#Secure"), "role":"Admin", "full_name":"ENEQ Admin", "email":""},
                {"username":"sales", "password_hash": hash_password("S@les2024#Secure"), "role":"Sales", "full_name":"Sales User", "email":""},
                {"username":"viewer", "password_hash": hash_password("View2024#Secure"), "role":"Viewer", "full_name":"Viewer User", "email":""},
            ])
            users.to_csv(self.users_path, index=False)
        if not self.settings_path.exists():
            self.save_settings(default_settings())
        if not self.quote_log_path.exists():
            pd.DataFrame(columns=["quote_number","version","quote_date","customer_company","customer_name","customer_email","project_name","bundle_type","quantity","subtotal_aed","margin_pct","discount_pct","grand_total_aed","prepared_by"]).to_csv(self.quote_log_path, index=False)

    def load_users(self) -> pd.DataFrame:
        self.ensure_default_files()
        return pd.read_csv(self.users_path).fillna("")

    def save_users(self, df: pd.DataFrame) -> None:
        df.to_csv(self.users_path, index=False)

    def load_settings(self) -> Dict:
        self.ensure_default_files()
        with open(self.settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # Override SMTP password with secure sources if available
        smtp_password = self._get_secure_smtp_password()
        if smtp_password:
            settings["smtp_password"] = smtp_password

        return settings

    def _get_secure_smtp_password(self) -> Optional[str]:
        """Get SMTP password from secure sources: Streamlit secrets or environment variables."""
        # Try Streamlit secrets first
        try:
            import streamlit as st
            # Check if secrets file exists and has the required structure
            if hasattr(st, 'secrets'):
                try:
                    secrets = st.secrets
                    if 'smtp' in secrets and 'password' in secrets.smtp:
                        return secrets.smtp.password
                except:
                    pass  # Secrets not available or malformed
        except ImportError:
            pass

        # Try environment variable
        env_password = os.getenv('SMTP_PASSWORD')
        if env_password:
            return env_password

        return None

    def save_settings(self, settings: Dict) -> None:
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    def append_quote_log(self, summary: Dict) -> None:
        self.ensure_default_files()
        row = {k: summary.get(k, "") for k in ["quote_number","version","quote_date","customer_company","customer_name","customer_email","project_name","bundle_type","quantity","subtotal_aed","margin_pct","discount_pct","grand_total_aed","prepared_by"]}
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
    """Calculate quote supporting both legacy (single bundle) and new (multi-bundle) modes."""
    
    pricing = repo.load_pricing()
    table_rows = []
    bundle_type_str = ""
    bundle_count = 0
    
    # Handle new multi-bundle mode
    if request.selected_bundles:
        for bundle_sel in request.selected_bundles:
            bundle_type = bundle_sel.get("bundle_type", "")
            bundle_qty = int(bundle_sel.get("quantity", 1))
            bundle_count += bundle_qty
            custom_components = bundle_sel.get("components", [])
            
            if not bundle_type_str:
                bundle_type_str = bundle_type
            elif bundle_type_str != "Multiple Bundles":
                bundle_type_str = "Multiple Bundles"
            
            # If custom components provided, use them; otherwise load from catalog
            if custom_components:
                # Custom components edited by user
                for comp in custom_components:
                    if comp.get("deleted"):
                        continue  # Skip deleted components
                    part_no = comp.get("part_no", "")
                    description = comp.get("description", "")
                    category = comp.get("category", "")
                    component_qty = int(comp.get("quantity", 1))
                    unit_price = float(comp.get("unit_price_aed", 0))
                    
                    total_qty = component_qty * bundle_qty
                    margin_mult = 1 + float(request.margin_pct) / 100.0
                    selling_price = unit_price * margin_mult
                    line_total = total_qty * selling_price
                    
                    table_rows.append({
                        "Part No": part_no,
                        "Description": description,
                        "Category": category,
                        "Qty / Bundle": component_qty,
                        "No. of Bundles": bundle_qty,
                        "Total Qty": total_qty,
                        "Unit Price (AED)": selling_price,
                        "Line Total (AED)": line_total,
                    })
            else:
                # Load from catalog
                components = repo.load_bundle_components()
                bundle_rows = components[components["bundle_type"] == bundle_type].copy()
                if bundle_rows.empty:
                    raise ValueError(f"No components found for bundle type: {bundle_type}")
                
                bundle_rows["quantity_per_bundle"] = pd.to_numeric(bundle_rows["quantity"], errors="coerce").fillna(0)
                bundle_rows["base_unit_price_aed"] = pd.to_numeric(bundle_rows["unit_price_aed"], errors="coerce").fillna(0)
                bundle_rows["selling_unit_price_aed"] = bundle_rows["base_unit_price_aed"] * (1 + float(request.margin_pct) / 100.0)
                bundle_rows["total_quantity"] = bundle_rows["quantity_per_bundle"] * bundle_qty
                bundle_rows["total_line_amount_aed"] = bundle_rows["total_quantity"] * bundle_rows["selling_unit_price_aed"]
                
                for _, row in bundle_rows.iterrows():
                    table_rows.append({
                        "Part No": str(row["part_no"]),
                        "Description": str(row["description"]),
                        "Category": str(row["category"]),
                        "Qty / Bundle": int(row["quantity_per_bundle"]),
                        "No. of Bundles": bundle_qty,
                        "Total Qty": int(row["total_quantity"]),
                        "Unit Price (AED)": float(row["selling_unit_price_aed"]),
                        "Line Total (AED)": float(row["total_line_amount_aed"]),
                    })
    else:
        # Legacy single-bundle mode (backward compatibility)
        components = repo.load_bundle_components()
        bundle_rows = components[components["bundle_type"] == request.bundle_type].copy()
        if bundle_rows.empty:
            raise ValueError(f"No components found for bundle type: {request.bundle_type}")
        
        bundle_rows["quantity_per_bundle"] = pd.to_numeric(bundle_rows["quantity"], errors="coerce").fillna(0)
        bundle_rows["base_unit_price_aed"] = pd.to_numeric(bundle_rows["unit_price_aed"], errors="coerce").fillna(0)
        bundle_rows["selling_unit_price_aed"] = bundle_rows["base_unit_price_aed"] * (1 + float(request.margin_pct) / 100.0)
        bundle_rows["requested_quantity"] = int(request.quantity)
        bundle_rows["total_quantity"] = bundle_rows["quantity_per_bundle"] * int(request.quantity)
        bundle_rows["total_line_amount_aed"] = bundle_rows["total_quantity"] * bundle_rows["selling_unit_price_aed"]
        
        bundle_type_str = request.bundle_type
        for _, row in bundle_rows.iterrows():
            table_rows.append({
                "Part No": str(row["part_no"]),
                "Description": str(row["description"]),
                "Category": str(row["category"]),
                "Qty / Bundle": int(row["quantity_per_bundle"]),
                "No. of Bundles": int(request.quantity),
                "Total Qty": int(row["total_quantity"]),
                "Unit Price (AED)": float(row["selling_unit_price_aed"]),
                "Line Total (AED)": float(row["total_line_amount_aed"]),
            })
    
    table_df = pd.DataFrame(table_rows)
    
    # Add additional services
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
    
    additional_df = pd.DataFrame(additional_rows) if additional_rows else pd.DataFrame()
    if not additional_df.empty:
        for col in table_df.columns:
            if col not in additional_df.columns:
                additional_df[col] = "-"
        additional_df = additional_df[table_df.columns]
        table_df = pd.concat([table_df, additional_df], ignore_index=True)
    
    # Calculate totals
    bundle_rows_df = pd.DataFrame(table_rows) if table_rows else table_df
    bundle_total = float(bundle_rows_df[bundle_rows_df["Part No"] != "SERVICE"]["Line Total (AED)"].sum()) if len(bundle_rows_df) > 0 else 0.0
    additional_total = float(additional_df["Line Total (AED)"].sum()) if not additional_df.empty else 0.0
    subtotal = bundle_total + additional_total
    discount_amount = subtotal * (request.discount_pct / 100.0)
    after_discount = subtotal - discount_amount
    vat_amount = after_discount * (request.vat_pct / 100.0)
    grand_total = after_discount + vat_amount
    
    details = get_bundle_details(repo, bundle_type_str) if bundle_type_str else {"bundle_name": "", "size": "", "mode": "", "family": ""}
    summary = {
        "quote_number": request.quote_number,
        "version": request.version,
        "quote_date": datetime.now().strftime("%d-%b-%Y"),
        "valid_until": (datetime.now() + pd.Timedelta(days=request.validity_days)).strftime("%d-%b-%Y"),
        "bundle_type": bundle_type_str or request.bundle_type,
        "size": request.size or details.get("size", ""),
        "mode": details.get("mode", ""),
        "quantity": bundle_count if request.selected_bundles else int(request.quantity),
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
        "attachments": request.attachments or [],
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

    # Create paragraph style for table cells
    styles.add(ParagraphStyle(name="TableCell", parent=styles["BodyText"], fontSize=8.5, leading=10, wordBreak="CJK"))
    
    meta_rows = [
        [_p("<b>Quote No.</b>", styles["TableCell"]), _p(summary["quote_number"], styles["TableCell"]), _p("<b>Version</b>", styles["TableCell"]), _p(summary.get("version", "1.0"), styles["TableCell"])],
        [_p("<b>Date</b>", styles["TableCell"]), _p(summary["quote_date"], styles["TableCell"]), _p("<b>Valid Until</b>", styles["TableCell"]), _p(summary["valid_until"], styles["TableCell"])],
        [_p("<b>Customer</b>", styles["TableCell"]), _p(summary["customer_name"] or "-", styles["TableCell"]), _p("<b>Company</b>", styles["TableCell"]), _p(summary["customer_company"] or "-", styles["TableCell"])],
        [_p("<b>Email</b>", styles["TableCell"]), _p(summary["customer_email"] or "-", styles["TableCell"]), _p("<b>Phone</b>", styles["TableCell"]), _p(summary["customer_phone"] or "-", styles["TableCell"])],
        [_p("<b>Project</b>", styles["TableCell"]), _p(summary["project_name"] or "-", styles["TableCell"]), _p("<b>Bundle</b>", styles["TableCell"]), _p(summary["bundle_type"], styles["TableCell"])],
        [_p("<b>Quantity</b>", styles["TableCell"]), _p(str(summary["quantity"]), styles["TableCell"]), _p("<b>Prepared By</b>", styles["TableCell"]), _p(summary.get("prepared_by", "-") or "-", styles["TableCell"])],
    ]
    meta_table = Table(meta_rows, colWidths=[24*mm, 62*mm, 25*mm, 69*mm])
    meta_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), light), ("BOX", (0,0), (-1,-1), 0.5, colors.grey), ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey), ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8.5), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5)]))
    story.extend([meta_table, Spacer(1, 8)])

    quote_table = table_df.copy().round(2)
    # Wrap table cell content in Paragraph for text wrapping
    styles.add(ParagraphStyle(name="ItemTableHeader", parent=styles["BodyText"], fontSize=7.4, leading=8, textColor=colors.white, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="ItemTableCell", parent=styles["BodyText"], fontSize=7.4, leading=8, wordBreak="CJK"))
    
    # Create header row with wrapped text
    header_row = [_p(str(col), styles["ItemTableHeader"]) for col in quote_table.columns.tolist()]
    # Create data rows with wrapped text
    data_rows = [[_p(str(val), styles["ItemTableCell"]) for val in row] for row in quote_table.values.tolist()]
    table_data = [header_row] + data_rows
    item_table = Table(table_data, repeatRows=1, colWidths=[22*mm, 54*mm, 21*mm, 17*mm, 20*mm, 17*mm, 23*mm, 24*mm])
    item_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), primary), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 7.4), ("GRID", (0,0), (-1,-1), 0.25, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP"), ("ALIGN", (3,1), (-1,-1), "RIGHT")]))
    story.extend([item_table, Spacer(1, 8)])

    styles.add(ParagraphStyle(name="TotalsCell", parent=styles["BodyText"], fontSize=9, leading=10, wordBreak="CJK"))
    styles.add(ParagraphStyle(name="TotalsCellBold", parent=styles["BodyText"], fontSize=9, leading=10, fontName="Helvetica-Bold", wordBreak="CJK"))
    
    totals_rows = []
    if float(summary.get("additional_services_total_aed", 0) or 0) > 0:
        totals_rows.extend([
            [_p("Bundle Total (AED)", styles["TotalsCell"]), _p(f"{summary.get('bundle_total_aed', 0):,.2f}", styles["TotalsCell"])],
            [_p("Additional Services (AED)", styles["TotalsCell"]), _p(f"{summary.get('additional_services_total_aed', 0):,.2f}", styles["TotalsCell"])],
        ])
    totals_rows.extend([
        [_p("Subtotal (AED)", styles["TotalsCell"]), _p(f"{summary['subtotal_aed']:,.2f}", styles["TotalsCell"])],
        [_p(f"Discount ({summary['discount_pct']:.2f}%)", styles["TotalsCell"]), _p(f"{summary['discount_amount_aed']:,.2f}", styles["TotalsCell"])],
        [_p(f"VAT ({summary['vat_pct']:.2f}%)", styles["TotalsCell"]), _p(f"{summary['vat_amount_aed']:,.2f}", styles["TotalsCell"])],
        [_p("<b>Grand Total (AED)</b>", styles["TotalsCellBold"]), _p(f"<b>{summary['grand_total_aed']:,.2f}</b>", styles["TotalsCellBold"])]
    ])
    totals_table = Table(totals_rows, colWidths=[54*mm, 38*mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 0.5, colors.grey), ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"), ("BACKGROUND", (0,-1), (-1,-1), light), ("ALIGN", (1,0), (1,-1), "RIGHT"), ("FONTSIZE", (0,0), (-1,-1), 9)]))
    story.extend([totals_table, Spacer(1, 8)])

    notes = summary.get("notes", "") or settings.get("terms", DEFAULT_TERMS)
    story.append(_p(f"<b>Commercial Terms / Notes:</b><br/>{notes}", styles["Small"]))
    
    # Add attachments note if any
    attachments = summary.get("attachments", [])
    if attachments:
        attachment_items = []
        for att in attachments:
            name = att.get("name", "File")
            size = att.get("size_mb", 0)
            attachment_items.append(f"• {name} ({size}MB)")
        attachment_list = "<br/>".join(attachment_items)
        story.append(Spacer(1, 6))
        story.append(_p(
            f"<b>📎 Attached Documents:</b><br/>{attachment_list}<br/><i>These files are embedded inside this PDF. Use your PDF viewer's attachment panel to download them.</i>",
            styles["Small"],
        ))
    
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
