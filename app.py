from __future__ import annotations

import re
from pathlib import Path

import openpyxl
import pandas as pd
import streamlit as st

from quotation_engine import (
    ASSET_DIR,
    DataRepository,
    QuoteRequest,
    authenticate,
    build_quote_pdf,
    calculate_quote,
    dataframe_to_csv_bytes,
    get_bundle_details,
    get_bundle_options,
    hash_password,
    send_quote_email,
)

st.set_page_config(page_title="ENEQ Quotation Generator", page_icon="📄", layout="wide")
repo = DataRepository()
repo.ensure_default_files()

CUSTOM_CSS = """
<style>
.stApp {background: linear-gradient(180deg, #f7fbff 0%, #eef4ff 100%);} 
.block-container {padding-top: 1.2rem;}
.hero {background: linear-gradient(135deg, #0f3d91 0%, #0b5fb3 100%); color: white; padding: 20px 24px; border-radius: 16px; margin-bottom: 16px;}
.card {background: white; padding: 16px; border-radius: 14px; border: 1px solid #dce7fb; box-shadow: 0 4px 18px rgba(15, 61, 145, 0.06);}
.small-note {color:#5f6b7a; font-size: 0.9rem;}
.danger-note {color:#b00020; font-size: 0.9rem; font-weight:600;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def parse_bundle_workbook(uploaded_file) -> tuple[pd.DataFrame, pd.DataFrame]:
    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.values)
    df = pd.DataFrame(rows[1:], columns=["_blank", "bundle_type", "part_no", "quantity", "price", "unique_bundle_type"])
    df = df.drop(columns=["_blank"])
    df = df[df["bundle_type"].notna()].copy()

    def parse_bundle(name: str) -> pd.Series:
        raw = str(name).strip()
        match = re.search(r'(\d+(?:\.\d+)?)\s*"', raw) or re.search(r'(\d+(?:\.\d+)?)', raw)
        size = f'{match.group(1)}"' if match else ""
        upper = raw.upper()
        mode = "Standalone USB Update" if "STANDALONE" in upper else "LAN Network" if "LAN NETWORK" in upper else "Multicasting" if "MULTICAST" in upper else "HDMI" if "HDMI" in upper else "Standard"
        family = "OPAL" if "OPAL" in upper else "Touchwo/Other"
        return pd.Series({"bundle_name": raw, "size": size, "mode": mode, "family": family})

    bundle_catalog = pd.DataFrame(sorted(df["bundle_type"].dropna().unique()), columns=["bundle_type"])
    bundle_catalog = bundle_catalog.join(bundle_catalog["bundle_type"].apply(parse_bundle))
    bundle_catalog["active"] = True
    pricing_df = repo.load_pricing()
    bundle_components = df[["bundle_type", "part_no", "quantity"]].copy()
    bundle_components = bundle_components.merge(pricing_df, on="part_no", how="left")
    bundle_components["line_amount_aed"] = pd.to_numeric(bundle_components["quantity"], errors="coerce").fillna(0) * pd.to_numeric(bundle_components["unit_price_aed"], errors="coerce").fillna(0)
    return bundle_catalog, bundle_components


def parse_pricing_workbook(uploaded_file) -> pd.DataFrame:
    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.values)
    pricing_df = pd.DataFrame(rows[1:], columns=["part_no", "description", "category", "unit_price_aed"])
    return pricing_df[pricing_df["part_no"].notna()].copy()


def login_box():
    st.markdown("<div class='hero'><h2 style='margin:0;'>ENEQ Solutions – Quotation Generator</h2><div>Secure login for sales quotation generation and admin catalogue control.</div></div>", unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
    if submitted:
        user = authenticate(repo, username, password)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.info("Default test users: admin/admin123, sales/sales123, viewer/viewer123. Change these immediately before production use.")

if "user" not in st.session_state:
    login_box()
    st.stop()

user = st.session_state["user"]
role = user.get("role", "Viewer")
settings = repo.load_settings()

st.markdown(f"""
<div class='hero'>
  <h2 style='margin:0;'>ENEQ Solutions – Elevator Digital Signage Quotation Generator</h2>
  <div style='margin-top:8px;'>Logged in as <b>{user.get('full_name', user.get('username'))}</b> | Role: <b>{role}</b></div>
</div>
""", unsafe_allow_html=True)
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

is_admin = role == "Admin"
is_sales = role in ["Admin", "Sales"]

tabs = ["Quotation Generator", "Quotation History"]
if is_admin:
    tabs += ["Admin / Catalog Update", "Users", "Company & Email Settings"]
selected_tabs = st.tabs(tabs)

with selected_tabs[0]:
    if not is_sales:
        st.warning("Your role has view-only access. Please contact the admin for quotation generation access.")
    else:
        col1, col2 = st.columns([1.15, 0.85])
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Customer & Project Details")
            c1, c2 = st.columns(2)
            customer_name = c1.text_input("Customer Contact Name")
            customer_company = c2.text_input("Customer Company")
            c3, c4 = st.columns(2)
            customer_email = c3.text_input("Customer Email")
            customer_phone = c4.text_input("Customer Phone")
            project_name = st.text_input("Project / Building Name")

            st.subheader("Quotation Inputs")
            bundle_options = get_bundle_options(repo)
            selected_bundle = st.selectbox("Bundle Type", bundle_options)
            details = get_bundle_details(repo, selected_bundle)
            c5, c6, c7 = st.columns(3)
            size = c5.text_input("Size", value=details.get("size", ""))
            quantity = c6.number_input("Quantity", min_value=1, value=1, step=1)
            default_margin = float(settings.get("default_margin_pct", 20.0))
            if is_admin:
                margin_pct = c7.number_input("Margin %", min_value=0.0, max_value=300.0, value=default_margin, step=0.5)
            else:
                margin_pct = default_margin
                c7.metric("Applied Margin %", f"{margin_pct:.2f}%")
            c8, c9, c10 = st.columns(3)
            max_discount = 100.0 if is_admin else float(settings.get("max_sales_discount_pct", 5.0))
            discount_pct = c8.number_input("Discount %", min_value=0.0, max_value=max_discount, value=0.0, step=0.5)
            vat_pct = c9.number_input("VAT %", min_value=0.0, max_value=100.0, value=float(settings.get("vat_pct", 5.0)), step=0.5)
            validity_days = c10.number_input("Validity Days", min_value=1, max_value=365, value=30, step=1)

            st.subheader("Additional Services (Optional)")
            st.caption("Select any required additional services. Enter unit price manually; system will multiply by service quantity and add it to the quotation total.")
            additional_services = []
            service_options = [
                "Installation / Testing & Commissioning",
                "CMS Server Unit with Accessories",
                "CMS Software Charges",
            ]
            for idx, service_name in enumerate(service_options, start=1):
                s1, s2, s3 = st.columns([2.3, 1, 1])
                selected_service = s1.checkbox(service_name, key=f"additional_service_selected_{idx}")
                unit_price = s2.number_input(
                    "Unit Price (AED)",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=f"additional_service_unit_price_{idx}",
                    disabled=not selected_service,
                )
                service_qty = s3.number_input(
                    "Quantity",
                    min_value=1,
                    value=int(quantity),
                    step=1,
                    key=f"additional_service_qty_{idx}",
                    disabled=not selected_service,
                )
                if selected_service:
                    additional_services.append({
                        "name": service_name,
                        "unit_price": float(unit_price),
                        "qty": int(service_qty),
                    })
            if additional_services:
                additional_preview = pd.DataFrame([
                    {
                        "Service": item["name"],
                        "Unit Price (AED)": item["unit_price"],
                        "Quantity": item["qty"],
                        "Line Total (AED)": item["unit_price"] * item["qty"],
                    }
                    for item in additional_services
                ])
                st.dataframe(additional_preview, use_container_width=True, hide_index=True)
                st.info(f"Additional Services Total: AED {additional_preview['Line Total (AED)'].sum():,.2f}")

            notes = st.text_area("Commercial Terms / Notes", value=settings.get("terms", ""), height=130)
            generate = st.button("Generate Quotation", type="primary", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Bundle Snapshot")
            st.write(f"**Family:** {details.get('family', '-')}")
            st.write(f"**Mode:** {details.get('mode', '-')}")
            st.write(f"**Detected Size:** {details.get('size', '-')}")
            preview = repo.load_bundle_components()
            preview = preview[preview["bundle_type"] == selected_bundle][["part_no", "description", "category", "quantity"]]
            st.dataframe(preview, use_container_width=True, hide_index=True)
            st.markdown("<div class='small-note'>Sales users can generate quotations using controlled margins and discount limits. Admin users can update catalogue, prices, users, logo and email settings.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if generate:
            request = QuoteRequest(
                customer_name=customer_name,
                customer_company=customer_company,
                customer_email=customer_email,
                customer_phone=customer_phone,
                project_name=project_name,
                bundle_type=selected_bundle,
                size=size,
                quantity=int(quantity),
                discount_pct=float(discount_pct),
                vat_pct=float(vat_pct),
                validity_days=int(validity_days),
                notes=notes,
                margin_pct=float(margin_pct),
                prepared_by=str(user.get("full_name", user.get("username", ""))),
                additional_services=additional_services,
            )
            summary, table_df = calculate_quote(repo, request)
            repo.append_quote_log(summary)
            pdf_bytes = build_quote_pdf(summary, table_df, settings)
            st.session_state["last_quote"] = {"summary": summary, "table_df": table_df, "pdf_bytes": pdf_bytes}
            st.success(f"Quotation {summary['quote_number']} generated.")

        if "last_quote" in st.session_state:
            q = st.session_state["last_quote"]
            summary, table_df, pdf_bytes = q["summary"], q["table_df"], q["pdf_bytes"]
            a, b, c, d = st.columns(4)
            a.metric("Subtotal (AED)", f"{summary['subtotal_aed']:,.2f}")
            b.metric("Addl. Services (AED)", f"{summary.get('additional_services_total_aed', 0):,.2f}")
            c.metric("VAT (AED)", f"{summary['vat_amount_aed']:,.2f}")
            d.metric("Grand Total (AED)", f"{summary['grand_total_aed']:,.2f}")
            st.caption(f"Discount Applied: AED {summary['discount_amount_aed']:,.2f}")
            st.subheader("Detailed Pricing")
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            d1, d2 = st.columns(2)
            d1.download_button("Download Branded Quotation PDF", data=pdf_bytes, file_name=f"{summary['quote_number']}.pdf", mime="application/pdf", use_container_width=True)
            d2.download_button("Download Pricing Breakdown CSV", data=dataframe_to_csv_bytes(table_df), file_name=f"{summary['quote_number']}_breakdown.csv", mime="text/csv", use_container_width=True)
            with st.expander("Send quotation by email"):
                email_to = st.text_input("To", value=summary.get("customer_email", ""))
                email_cc = st.text_input("CC")
                email_subject = st.text_input("Subject", value=f"ENEQ Solutions Quotation - {summary['quote_number']}")
                email_body = st.text_area("Email Body", value=f"Dear {summary.get('customer_name') or 'Customer'},\n\nPlease find attached our quotation for {summary.get('project_name') or 'your requirement'}.\n\nRegards,\nENEQ Solutions")
                if st.button("Send Email", use_container_width=True):
                    try:
                        send_quote_email(settings, email_to, email_subject, email_body, pdf_bytes, f"{summary['quote_number']}.pdf", cc=email_cc)
                        st.success("Email sent successfully.")
                    except Exception as e:
                        st.error(f"Email could not be sent: {e}")

with selected_tabs[1]:
    st.subheader("Quotation History")
    log = repo.load_quote_log()
    st.dataframe(log.sort_values("quote_number", ascending=False), use_container_width=True, hide_index=True)
    st.download_button("Download Quote Log CSV", data=dataframe_to_csv_bytes(log), file_name="eneq_quote_log.csv", mime="text/csv")

if is_admin:
    with selected_tabs[2]:
        left, right = st.columns(2)
        with left:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Update Pricing")
            pricing_file = st.file_uploader("Upload Pricing Workbook", type=["xlsx"], key="pricing_upload")
            if pricing_file is not None:
                pricing_df = parse_pricing_workbook(pricing_file)
                st.dataframe(pricing_df.head(20), use_container_width=True, hide_index=True)
                if st.button("Replace Pricing Master", use_container_width=True):
                    repo.save_pricing(pricing_df)
                    st.success("Pricing master updated successfully.")
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Update Bundle Types")
            bundle_file = st.file_uploader("Upload Bundle Workbook", type=["xlsx"], key="bundle_upload")
            if bundle_file is not None:
                bundle_catalog, bundle_components = parse_bundle_workbook(bundle_file)
                st.dataframe(bundle_catalog.head(20), use_container_width=True, hide_index=True)
                if st.button("Replace Bundle Catalog", use_container_width=True):
                    repo.save_bundle_catalog(bundle_catalog)
                    repo.save_bundle_components(bundle_components)
                    st.success("Bundle catalog updated successfully.")
            st.markdown("</div>", unsafe_allow_html=True)
        st.subheader("Current Master Data")
        c1, c2 = st.columns(2)
        c1.dataframe(repo.load_bundle_catalog(), use_container_width=True, hide_index=True)
        c2.dataframe(repo.load_pricing(), use_container_width=True, hide_index=True)

    with selected_tabs[3]:
        st.subheader("User Management")
        users = repo.load_users()
        show_users = users.drop(columns=["password_hash"], errors="ignore")
        st.dataframe(show_users, use_container_width=True, hide_index=True)
        with st.form("add_user"):
            st.write("Add / Replace User")
            u1, u2, u3 = st.columns(3)
            new_username = u1.text_input("Username")
            new_fullname = u2.text_input("Full Name")
            new_role = u3.selectbox("Role", ["Admin", "Sales", "Viewer"])
            u4, u5 = st.columns(2)
            new_email = u4.text_input("Email")
            new_password = u5.text_input("Password", type="password")
            save_user = st.form_submit_button("Save User", type="primary")
        if save_user:
            if not new_username or not new_password:
                st.error("Username and password are required.")
            else:
                users = users[users["username"].astype(str).str.lower() != new_username.lower()]
                users = pd.concat([users, pd.DataFrame([{"username": new_username, "password_hash": hash_password(new_password), "role": new_role, "full_name": new_fullname, "email": new_email}])], ignore_index=True)
                repo.save_users(users)
                st.success("User saved successfully.")
                st.rerun()

    with selected_tabs[4]:
        st.subheader("Company Branding & Email Settings")
        with st.form("settings_form"):
            c1, c2 = st.columns(2)
            settings["company_name"] = c1.text_input("Company Name", value=settings.get("company_name", ""))
            settings["company_website"] = c2.text_input("Website", value=settings.get("company_website", ""))
            settings["company_address"] = st.text_input("Address", value=settings.get("company_address", ""))
            c3, c4 = st.columns(2)
            settings["company_email"] = c3.text_input("Company Email", value=settings.get("company_email", ""))
            settings["company_phone"] = c4.text_input("Company Phone", value=settings.get("company_phone", ""))
            c5, c6, c7 = st.columns(3)
            settings["vat_pct"] = c5.number_input("Default VAT %", value=float(settings.get("vat_pct", 5.0)))
            settings["default_margin_pct"] = c6.number_input("Default Margin %", value=float(settings.get("default_margin_pct", 20.0)))
            settings["max_sales_discount_pct"] = c7.number_input("Max Sales Discount %", value=float(settings.get("max_sales_discount_pct", 5.0)))
            settings["terms"] = st.text_area("Default Commercial Terms", value=settings.get("terms", ""), height=150)
            st.write("Email / SMTP")
            e1, e2 = st.columns(2)
            settings["smtp_host"] = e1.text_input("SMTP Host", value=settings.get("smtp_host", ""))
            settings["smtp_port"] = e2.number_input("SMTP Port", value=int(settings.get("smtp_port", 587)), step=1)
            e3, e4 = st.columns(2)
            settings["smtp_username"] = e3.text_input("SMTP Username / Sender Email", value=settings.get("smtp_username", ""))
            settings["smtp_password"] = e4.text_input("SMTP Password / App Password", value=settings.get("smtp_password", ""), type="password")
            settings["email_sender_name"] = st.text_input("Sender Name", value=settings.get("email_sender_name", "ENEQ Solutions"))
            settings["smtp_use_tls"] = st.checkbox("Use TLS", value=bool(settings.get("smtp_use_tls", True)))
            saved = st.form_submit_button("Save Settings", type="primary")
        logo_file = st.file_uploader("Upload ENEQ Logo", type=["png", "jpg", "jpeg"], key="logo_upload")
        if logo_file is not None:
            suffix = Path(logo_file.name).suffix.lower()
            logo_path = ASSET_DIR / f"eneq_logo{suffix}"
            logo_path.write_bytes(logo_file.getvalue())
            settings["logo_path"] = str(logo_path)
            repo.save_settings(settings)
            st.success("Logo uploaded and saved.")
        if saved:
            repo.save_settings(settings)
            st.success("Settings saved successfully.")
