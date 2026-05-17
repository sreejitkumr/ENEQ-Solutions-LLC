# ENEQ Solutions Quotation Generator

Streamlit app for elevator digital signage bundle quotation generation.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Default test logins

**⚠️ CRITICAL: Change these default passwords immediately after first login!**

| Username | Password | Role |
|---|---|---|
| admin | Adm!n2024#Secure | Admin |
| sales | S@les2024#Secure | Sales |
| viewer | View2024#Secure | Viewer |

## Security Setup (Required for Production)

### 1. SMTP Password Security

**NEVER store SMTP passwords in plain text!** Use one of these secure methods:

#### Option A: Streamlit Secrets (Recommended for Streamlit Cloud)
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Fill in your actual SMTP password:
   ```toml
   [smtp]
   password = "your-actual-smtp-password"
   ```
3. **Never commit `secrets.toml` to version control**

#### Option B: Environment Variables (Recommended for other platforms)
Set the environment variable:
```bash
export SMTP_PASSWORD="your-actual-smtp-password"
```

### 2. User Management
- Change all default passwords immediately
- Create individual user accounts for each team member
- Use strong, unique passwords
- Regularly rotate passwords

### 3. Data Security
- The `data/` directory contains sensitive business data
- Regularly back up this directory
- Consider encrypting sensitive files in production
- Never commit user data or settings to version control

## Email setup

In `Company & Email Settings`, configure SMTP host, port, username.

For Gmail or Microsoft 365, use an app password or authenticated SMTP account. **Do not use your normal mailbox password in production.**

The SMTP password will be securely loaded from Streamlit secrets or environment variables.

## Roles

- Admin: catalogue, pricing, margin, users, email settings and quotation generation
- Sales: quotation generation with controlled default margin and capped discount
- Viewer: quotation history view only

## Production recommendations

- ✅ **Replace default test passwords immediately** (see Security Setup above)
- ✅ **Use Streamlit secrets or environment variables for SMTP password** (see Security Setup above)
- ✅ **Restrict access to HTTPS** (automatic on most deployment platforms)
- ✅ **Back up `/data` directory regularly**
- ✅ **Review generated PDF before sending to customers**
- ✅ **Use strong passwords for all user accounts**
- ✅ **Regularly update dependencies**
- ✅ **Monitor application logs for security issues**
- ✅ **Consider implementing rate limiting for login attempts**

## Deployment Options

### Streamlit Cloud (Recommended)
1. Push code to a **public** GitHub repository
2. Set up `.streamlit/secrets.toml` with your SMTP password
3. Deploy at [share.streamlit.io](https://share.streamlit.io)

### Heroku
1. Create `Procfile`:
   ```
   web: streamlit run app.py --server.port $PORT --server.headless true
   ```
2. Set environment variable: `SMTP_PASSWORD=your-password`
3. Deploy: `git push heroku main`

### Railway / Render
1. Connect GitHub repository
2. Set environment variable: `SMTP_PASSWORD=your-password`
3. Deploy automatically

### Local Production Server
```bash
export SMTP_PASSWORD="your-password"
streamlit run app.py --server.port 8501 --server.headless true
```

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
# ENEQ-Solutions-LLC
