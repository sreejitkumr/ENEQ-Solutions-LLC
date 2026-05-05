# Cursor Build Brief – ENEQ Quotation Generator Enhancements

## Objective
Enhance the existing Streamlit quotation generator into a secure ENEQ-branded commercial quotation tool for elevator digital signage bundles.

## Core Features Implemented
1. Role-based login
   - Admin, Sales, Viewer roles
   - Default CSV-based user store for quick deployment
   - Passwords are SHA-256 hashed

2. ENEQ branded PDF
   - Uploadable ENEQ logo
   - Company details in PDF header
   - Quote meta table
   - Commercial line items
   - Totals, VAT, discount and terms

3. Customer data capture
   - Customer contact name
   - Company
   - Email
   - Phone
   - Project/building name

4. Margin control
   - Admin can set default margin
   - Admin can override margin at quotation time
   - Sales users use default margin only
   - Sales discount is capped by admin setting

5. Email sending
   - SMTP settings maintained by admin
   - Sends generated PDF as attachment
   - Supports CC

6. Admin maintenance
   - Upload updated Bundle Types workbook
   - Upload updated Pricing workbook
   - Manage users
   - Manage company, logo, VAT, margin and commercial terms

## Recommended Future Improvements
- Move users and quotes from CSV to SQLite/PostgreSQL
- Add quotation approval workflow when discount exceeds threshold
- Add customer master database
- Add item-level manual override subject to admin approval
- Add revision numbers: ENEQ-Q-YYYYMMDD-001-R1
- Add separate internal costing sheet vs customer quotation
- Add e-signature or quote acceptance link
