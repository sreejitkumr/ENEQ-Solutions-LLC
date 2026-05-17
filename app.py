from __future__ import annotations

import re
from pathlib import Path
import uuid
import io

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


# File handling constants
ALLOWED_EXTENSIONS = {'.pdf', '.jpeg', '.jpg', '.png', '.doc', '.xls', '.docx', '.xlsx'}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ATTACHMENTS_DIR = ASSET_DIR / "attachments"
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)


def validate_attachment(uploaded_file) -> tuple[bool, str]:
    """Validate file type and size."""
    if uploaded_file is None:
        return False, ""
    
    file_ext = Path(uploaded_file.name).suffix.lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"❌ File type '{file_ext}' not allowed. Supported: PDF, JPEG, JPG, PNG, DOC, DOCX, XLS, XLSX"
    
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        size_mb = uploaded_file.size / (1024 * 1024)
        return False, f"❌ File size {size_mb:.2f}MB exceeds {MAX_FILE_SIZE_MB}MB limit"
    
    return True, "✅ File valid"


def save_attachment(uploaded_file) -> tuple[bool, str, str | None]:
    """Save attachment to session state and return unique ID."""
    is_valid, message = validate_attachment(uploaded_file)
    
    if not is_valid:
        return False, message, None
    
    # Create a unique ID for this file
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}_{uploaded_file.name}"
    file_path = ATTACHMENTS_DIR / file_name
    file_bytes = uploaded_file.getvalue()
    
    # Save to disk so PDF links can resolve to an actual file path
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    
    # Store in session state
    if "attachments" not in st.session_state:
        st.session_state.attachments = {}
    
    st.session_state.attachments[file_id] = {
        "name": uploaded_file.name,
        "data": file_bytes,
        "size_mb": round(uploaded_file.size / (1024 * 1024), 2),
        "path": str(file_path.resolve()),
    }
    
    return True, message, file_id


def load_bundle_components_for_bundle(repo: DataRepository, bundle_type: str) -> list[dict]:
    components = repo.load_bundle_components()
    bundle_rows = components[components["bundle_type"] == bundle_type].copy()
    if bundle_rows.empty:
        return []
    bundle_rows["quantity"] = pd.to_numeric(bundle_rows["quantity"], errors="coerce").fillna(0)
    bundle_rows["unit_price_aed"] = pd.to_numeric(bundle_rows["unit_price_aed"], errors="coerce").fillna(0.0)

    records = []
    for _, row in bundle_rows.iterrows():
        records.append({
            "part_no": str(row.get("part_no", "") or ""),
            "description": str(row.get("description", "") or ""),
            "category": str(row.get("category", "") or ""),
            "quantity": int(row["quantity"]),
            "unit_price_aed": float(row["unit_price_aed"]),
            "deleted": False,
        })
    return records


def render_bundle_components_editor(bundle_sel: dict, idx: int, repo: DataRepository) -> None:
    if "components" not in bundle_sel or bundle_sel["components"] is None:
        bundle_sel["components"] = []
    if not bundle_sel["components"]:
        bundle_sel["components"] = load_bundle_components_for_bundle(repo, bundle_sel["bundle_type"])

    st.write("**Bundle Components:**")
    if not bundle_sel["components"]:
        st.info("No components found for this bundle.")

    for comp_idx, comp in enumerate(bundle_sel["components"]):
        if comp.get("deleted"):
            continue

        comp_col1, comp_col2, comp_col3, comp_col4, comp_col5 = st.columns([0.2, 0.25, 0.15, 0.2, 0.2])

        with comp_col1:
            st.caption("**Part No**")
            bundle_sel["components"][comp_idx]["part_no"] = st.text_input(
                "Part No",
                value=comp.get("part_no", ""),
                label_visibility="collapsed",
                key=f"comp_part_{idx}_{comp_idx}"
            )

        with comp_col2:
            st.caption("**Description**")
            bundle_sel["components"][comp_idx]["description"] = st.text_input(
                "Description",
                value=comp.get("description", ""),
                label_visibility="collapsed",
                key=f"comp_desc_{idx}_{comp_idx}"
            )

        with comp_col3:
            st.caption("**Qty**")
            bundle_sel["components"][comp_idx]["quantity"] = st.number_input(
                "Quantity",
                min_value=1,
                value=int(comp.get("quantity", 1)),
                step=1,
                label_visibility="collapsed",
                key=f"comp_qty_{idx}_{comp_idx}"
            )

        with comp_col4:
            st.caption("**Price (AED)**")
            bundle_sel["components"][comp_idx]["unit_price_aed"] = st.number_input(
                "Unit Price",
                min_value=0.0,
                value=float(comp.get("unit_price_aed", 0)),
                step=10.0,
                label_visibility="collapsed",
                key=f"comp_price_{idx}_{comp_idx}"
            )

        with comp_col5:
            st.write("")
            if st.button("❌", key=f"delete_comp_{idx}_{comp_idx}", help="Delete component"):
                bundle_sel["components"][comp_idx]["deleted"] = True
                st.rerun()

    if st.button("➕ Add Component", key=f"add_component_{idx}", use_container_width=True):
        bundle_sel["components"].append({
            "part_no": "",
            "description": "",
            "category": "",
            "quantity": 1,
            "unit_price_aed": 0.0,
            "deleted": False,
        })
        st.rerun()


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
        col1, col2 = st.columns([1.0, 1.0])
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
            q1, q2 = st.columns(2)
            quote_number = q1.text_input("Zoho Books Quote Number", placeholder="e.g., ZB-2024-001", help="Enter the quote number from Zoho Books")
            version = q2.text_input("Quote Version", value="1.0", placeholder="e.g., 1.0, 2.0, 1.1", help="Version number for tracking quote revisions")
            
            # Initialize bundle selection session state
            if "selected_bundles" not in st.session_state:
                st.session_state.selected_bundles = []
            
            # Bundle selection mode toggle
            bundle_mode = st.radio("Bundle Selection Mode", ["Single Bundle", "Multiple Bundles"], horizontal=True, help="Select single or multiple bundles for this quotation")
            
            bundle_options = get_bundle_options(repo)
            selected_bundles_list = []
            
            if bundle_mode == "Single Bundle":
                selected_bundle = st.selectbox("Bundle Type", bundle_options, key="single_bundle_select")
                details = get_bundle_details(repo, selected_bundle)
                c5, c6, c7 = st.columns(3)
                size = c5.text_input("Size", value=details.get("size", ""))
                quantity = c6.number_input("Quantity", min_value=1, value=1, step=1, key="single_bundle_qty")

                if not st.session_state.selected_bundles or len(st.session_state.selected_bundles) != 1 or st.session_state.selected_bundles[0]["bundle_type"] != selected_bundle:
                    st.session_state.selected_bundles = [{
                        "bundle_type": selected_bundle,
                        "quantity": int(quantity),
                        "components": load_bundle_components_for_bundle(repo, selected_bundle),
                        "id": "single_bundle",
                    }]
                else:
                    st.session_state.selected_bundles[0]["quantity"] = int(quantity)

                bundle_sel = st.session_state.selected_bundles[0]
                with st.expander(f"🔧 Edit Components for {selected_bundle}", expanded=True):
                    render_bundle_components_editor(bundle_sel, 0, repo)

                selected_bundles_list = st.session_state.selected_bundles
            else:
                size = ""
                quantity = 1
                st.write("**Add or Edit Bundles:**")

                col_bundle, col_qty, col_action = st.columns([0.4, 0.2, 0.4])
                with col_bundle:
                    new_bundle = st.selectbox("Select Bundle to Add", bundle_options, key="multi_bundle_select")
                with col_qty:
                    new_qty = st.number_input("Qty", min_value=1, value=1, step=1, key="multi_bundle_qty")
                with col_action:
                    st.write("")  # Spacer
                    if st.button("➕ Add Bundle", use_container_width=True):
                        if "selected_bundles" not in st.session_state:
                            st.session_state.selected_bundles = []
                        st.session_state.selected_bundles.append({
                            "bundle_type": new_bundle,
                            "quantity": int(new_qty),
                            "components": [],
                            "id": str(len(st.session_state.selected_bundles))
                        })
                        st.rerun()

                if st.session_state.selected_bundles:
                    st.markdown("---")
                    st.write("**Selected Bundles:**")
                    for idx, bundle_sel in enumerate(st.session_state.selected_bundles):
                        with st.expander(f"🔧 {bundle_sel['bundle_type']} (Qty: {bundle_sel['quantity']})", expanded=False):
                            exp_col1, exp_col2, exp_col3 = st.columns([0.35, 0.3, 0.35])

                            with exp_col1:
                                st.session_state.selected_bundles[idx]["quantity"] = st.number_input(
                                    "Bundle Quantity",
                                    min_value=1,
                                    value=bundle_sel["quantity"],
                                    step=1,
                                    key=f"edit_bundle_qty_{idx}"
                                )

                            with exp_col3:
                                st.write("")  # Spacer
                                if st.button("🗑️ Remove Bundle", key=f"remove_bundle_{idx}", use_container_width=True):
                                    st.session_state.selected_bundles.pop(idx)
                                    st.rerun()

                            render_bundle_components_editor(bundle_sel, idx, repo)

                selected_bundles_list = st.session_state.selected_bundles if st.session_state.selected_bundles else []

            default_margin = float(settings.get("default_margin_pct", 20.0))
            c7, c8, c9 = st.columns(3)
            if is_admin:
                margin_pct = c7.number_input("Margin %", min_value=0.0, max_value=300.0, value=default_margin, step=0.5)
            else:
                margin_pct = default_margin
                c7.metric("Applied Margin %", f"{margin_pct:.2f}%")
            max_discount = 100.0 if is_admin else float(settings.get("max_sales_discount_pct", 5.0))
            discount_pct = c8.number_input("Discount %", min_value=0.0, max_value=max_discount, value=0.0, step=0.5)
            vat_pct = c9.number_input("VAT %", min_value=0.0, max_value=100.0, value=float(settings.get("vat_pct", 5.0)), step=0.5)
            validity_days = st.number_input("Validity Days", min_value=1, max_value=365, value=30, step=1)

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
                    "Service Quantity",
                    min_value=1,
                    value=1,
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

            # File Attachments Section
            st.subheader("Attachments (Optional)")
            st.caption(f"Attach supporting documents (PDF, JPEG, JPG, PNG, DOC, DOCX, XLS, XLSX). Max {MAX_FILE_SIZE_MB}MB per file.")
            
            # Initialize attachment tracking
            if "processed_files" not in st.session_state:
                st.session_state.processed_files = set()
            
            attachment_files = []
            uploaded_file = st.file_uploader(
                "Upload files",
                type=['pdf', 'jpeg', 'jpg', 'png', 'doc', 'docx', 'xls', 'xlsx'],
                key="quotation_attachment_uploader",
                accept_multiple_files=False,
                help="Upload supporting documents to attach to this quotation"
            )
            
            # Process uploaded file only if it hasn't been processed before
            if uploaded_file is not None:
                file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if file_key not in st.session_state.processed_files:
                    is_valid, validation_msg = validate_attachment(uploaded_file)
                    if is_valid:
                        success, save_msg, file_id = save_attachment(uploaded_file)
                        if success:
                            st.session_state.processed_files.add(file_key)
                            st.success(f"📎 {uploaded_file.name} ({round(uploaded_file.size / (1024*1024), 2)}MB) - {save_msg}")
                            attachment_files.append({
                                "name": uploaded_file.name,
                                "file_id": file_id,
                                "size_mb": round(uploaded_file.size / (1024*1024), 2)
                            })
                    else:
                        st.error(validation_msg)
            
            # Display attached files with remove button
            if "attachments" in st.session_state and st.session_state.attachments:
                st.write("**Attached Files:**")
                for file_id, file_info in st.session_state.attachments.items():
                    col_file, col_btn = st.columns([4, 1])
                    col_file.write(f"📎 {file_info['name']} ({file_info['size_mb']}MB)")
                    if col_btn.button("❌ Remove", key=f"remove_attachment_{file_id}", help="Click to remove this file"):
                        # Remove file from session state
                        if file_id in st.session_state.attachments:
                            del st.session_state.attachments[file_id]
                        st.success(f"File removed successfully!", icon="✅")
                        # Rerun to refresh the UI and hide the removed file
                        st.rerun()

            notes = st.text_area("Commercial Terms / Notes", value=settings.get("terms", ""), height=130)
            generate = st.button("Generate Quotation", type="primary", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            if bundle_mode == "Single Bundle":
                st.subheader("📦 Bundle Snapshot")
                # Display bundle details in a more compact format
                detail_col1, detail_col2 = st.columns(2)
                with detail_col1:
                    st.write(f"**Family:**\n{details.get('family', '-')}")
                    st.write(f"**Mode:**\n{details.get('mode', '-')}")
                with detail_col2:
                    st.write(f"**Size:**\n{details.get('size', '-')}")
                
                st.markdown("---")
                st.caption("**Components in this Bundle:**")
                preview = repo.load_bundle_components()
                preview = preview[preview["bundle_type"] == selected_bundle][["part_no", "description", "category", "quantity"]]
                
                # Display with smaller font to fit better
                if len(preview) > 0:
                    st.dataframe(
                        preview.rename(columns={
                            "part_no": "Part",
                            "description": "Description",
                            "category": "Category",
                            "quantity": "Qty"
                        }),
                        use_container_width=True,
                        hide_index=True,
                        height=250
                    )
                else:
                    st.info("No components found for this bundle")
            else:
                st.subheader("📦 Selected Bundles Summary")
                if st.session_state.selected_bundles:
                    summary_data = []
                    for bundle_sel in st.session_state.selected_bundles:
                        bundle_name = bundle_sel['bundle_type']
                        bundle_qty = bundle_sel['quantity']
                        comp_count = len([c for c in bundle_sel.get('components', []) if not c.get('deleted', False)])
                        summary_data.append({
                            "Bundle": bundle_name,
                            "Qty": bundle_qty,
                            "Components": comp_count if comp_count > 0 else "Default"
                        })
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No bundles selected. Add bundles above to continue.")
            
            st.markdown("<div class='small-note'><b>Role Info:</b> Sales users can generate quotations with controlled margins and discounts. Admin users can manage catalogue, prices, users, and settings.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if generate:
            # Validate quote number
            if not quote_number or not quote_number.strip():
                st.error("❌ Please enter the Zoho Books Quote Number before generating the quotation.")
            elif not version or not version.strip():
                st.error("❌ Please enter the Quote Version before generating the quotation.")
            elif not selected_bundles_list:
                st.error("❌ Please select at least one bundle before generating the quotation.")
            else:
                # Prepare attachments list
                attachments_list = []
                if "attachments" in st.session_state:
                    for file_id, file_info in st.session_state.attachments.items():
                        attachments_list.append({
                            "file_id": file_id,
                            "name": file_info["name"],
                            "size_mb": file_info["size_mb"],
                            "path": file_info.get("path", ""),
                        })

                for bundle_sel in selected_bundles_list:
                    bundle_sel["components"] = [c for c in bundle_sel.get("components", []) if not c.get("deleted", False)]

                request = QuoteRequest(
                    customer_name=customer_name,
                    customer_company=customer_company,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    project_name=project_name,
                    bundle_type=selected_bundles_list[0]["bundle_type"],
                    size=size,
                    quantity=int(quantity),
                    quote_number=quote_number.strip(),
                    version=version.strip(),
                    discount_pct=float(discount_pct),
                    vat_pct=float(vat_pct),
                    validity_days=int(validity_days),
                    notes=notes,
                    margin_pct=float(margin_pct),
                    prepared_by=str(user.get("full_name", user.get("username", ""))),
                    selected_bundles=selected_bundles_list,
                    additional_services=additional_services,
                    attachments=attachments_list,
                )
                summary, table_df = calculate_quote(repo, request)
                repo.append_quote_log(summary)
                pdf_bytes = build_quote_pdf(summary, table_df, settings)
                # Attachment embedding disabled to restore stable PDF generation.
                st.session_state["last_quote"] = {"summary": summary, "table_df": table_df, "pdf_bytes": pdf_bytes}
                st.success(f"✅ Quotation {summary['quote_number']} v{summary['version']} generated successfully!")

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
            
            # Download attachments if any
            if summary.get("attachments"):
                st.subheader("📎 Attached Documents")
                att_cols = st.columns(len(summary.get("attachments", [])))
                for idx, attachment in enumerate(summary.get("attachments", [])):
                    with att_cols[idx]:
                        file_id = attachment.get("file_id")
                        file_name = attachment.get("name")
                        if "attachments" in st.session_state and file_id in st.session_state.attachments:
                            file_data = st.session_state.attachments[file_id]["data"]
                            st.download_button(
                                f"📥 {file_name}",
                                data=file_data,
                                file_name=file_name,
                                mime="application/octet-stream",
                                use_container_width=True
                            )
            
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

        if "show_new_user_form" not in st.session_state:
            st.session_state.show_new_user_form = False
        if "show_reset_password" not in st.session_state:
            st.session_state.show_reset_password = False

        left, right = st.columns([2, 1])
        with left:
            st.write("### Existing Users")
            st.markdown("Select a user from the table to edit or delete them.")
            st.dataframe(show_users, use_container_width=True, hide_index=True)

        with right:
            if not show_users.empty:
                selected_user = st.selectbox("Select user to manage", show_users["username"].tolist(), key="selected_user")
            else:
                selected_user = None

            if st.button("➕ Create New User", type="secondary", use_container_width=True, key="new_user_button"):
                st.session_state.show_new_user_form = True
                st.session_state.show_reset_password = False

            if selected_user:
                selected_row = users[users["username"] == selected_user].iloc[0]
                st.markdown("---")
                st.write(f"### Edit {selected_user}")
                with st.form("edit_user_form"):
                    edit_fullname = st.text_input("Full Name", value=selected_row.get("full_name", ""))
                    edit_role = st.selectbox("Role", ["Admin", "Sales", "Viewer"], index=["Admin", "Sales", "Viewer"].index(str(selected_row.get("role", "Viewer"))))
                    edit_email = st.text_input("Email", value=selected_row.get("email", ""))
                    save_changes = st.form_submit_button("Save Changes", type="primary")
                if save_changes:
                    users.loc[users["username"] == selected_user, "full_name"] = edit_fullname
                    users.loc[users["username"] == selected_user, "role"] = edit_role
                    users.loc[users["username"] == selected_user, "email"] = edit_email
                    repo.save_users(users)
                    st.success("User details updated successfully.")
                    st.rerun()

                st.markdown("---")
                if st.button("🔒 Reset Password", use_container_width=True, key="reset_password_toggle"):
                    st.session_state.show_reset_password = not st.session_state.show_reset_password

                if st.session_state.show_reset_password:
                    with st.form("reset_password_form"):
                        reset_password = st.text_input("New Password", type="password")
                        reset_password_confirm = st.text_input("Confirm New Password", type="password")
                        reset_password_button = st.form_submit_button("Reset Password", type="primary")
                    if reset_password_button:
                        if not reset_password:
                            st.error("Enter a new password to reset.")
                        elif reset_password != reset_password_confirm:
                            st.error("Passwords do not match.")
                        else:
                            users.loc[users["username"] == selected_user, "password_hash"] = hash_password(reset_password)
                            repo.save_users(users)
                            st.success(f"Password for {selected_user} has been reset.")
                            st.session_state.show_reset_password = False
                            st.rerun()

                st.markdown("---")
                if selected_user == user.get("username", ""):
                    st.warning("You cannot delete the currently logged-in account.")
                else:
                    if st.button("🗑️ Delete User", type="secondary", use_container_width=True, key="delete_user_button"):
                        users = users[users["username"] != selected_user]
                        repo.save_users(users)
                        st.success(f"User {selected_user} deleted.")
                        st.rerun()

        if st.session_state.show_new_user_form:
            st.markdown("---")
            st.subheader("Create New User")
            with st.form("add_user_form"):
                a1, a2, a3 = st.columns(3)
                new_username = a1.text_input("Username")
                new_fullname = a2.text_input("Full Name")
                new_role = a3.selectbox("Role", ["Admin", "Sales", "Viewer"])
                a4, a5 = st.columns(2)
                new_email = a4.text_input("Email")
                new_password = a5.text_input("Password", type="password")
                create_user = st.form_submit_button("Create User", type="primary")
            if create_user:
                if not new_username or not new_password:
                    st.error("Username and password are required.")
                else:
                    users = users[users["username"].astype(str).str.lower() != new_username.lower()]
                    users = pd.concat([users, pd.DataFrame([{"username": new_username, "password_hash": hash_password(new_password), "role": new_role, "full_name": new_fullname, "email": new_email}])], ignore_index=True)
                    repo.save_users(users)
                    st.success("User created successfully.")
                    st.session_state.show_new_user_form = False
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
