# ENEQ Solutions Quotation Generator

Streamlit app for elevator digital signage bundle quotation generation.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Default test logins

Change these before production.

| Username | Password | Role |
|---|---|---|
| admin | admin123 | Admin |
| sales | sales123 | Sales |
| viewer | viewer123 | Viewer |

## New features

- ENEQ branded PDF quotation with logo support
- Customer details and project details
- Auto email sending with PDF attachment using SMTP
- Margin control and sales discount limit
- Multi-user login with Admin, Sales and Viewer roles
- Admin upload for Bundle Types and Pricing masters
- Quotation history log

## Email setup

In `Company & Email Settings`, configure SMTP host, port, username and app password.

For Gmail or Microsoft 365, use an app password or authenticated SMTP account. Do not use your normal mailbox password in production.

## Roles

- Admin: catalogue, pricing, margin, users, email settings and quotation generation
- Sales: quotation generation with controlled default margin and capped discount
- Viewer: quotation history view only

## Production recommendations

- Replace default test passwords immediately
- Restrict access to HTTPS
- Use environment variables or Streamlit secrets for SMTP password in production
- Back up `/data` regularly
- Review generated PDF before sending to customers

## Additional Services Feature

The quotation input screen now includes optional additional services:

1. Installation / Testing & Commissioning
2. CMS Server Unit with Accessories
3. CMS Software Charges

For each selected service, the user can manually enter:
- Unit Price (AED)
- Quantity

The application calculates:
`Additional Service Total = Unit Price × Quantity`

The additional service rows are added to the detailed quotation table, included in subtotal, VAT and grand total, and reflected in the branded PDF quotation and email attachment.
