# AdSense Activation Checklist

## Pre-requisites
- [ ] AdSense account approved
- [ ] Site live on real domain with HTTPS
- [ ] Privacy Policy page live at /privacy
- [ ] Cookie consent banner live and working

## Steps

### 1. Get your publisher ID and ad slot IDs
- Log into https://adsense.google.com
- Publisher ID format: ca-pub-XXXXXXXXXXXXXXXXXX (16 digits)
- Create 3 ad units (dashboard-hero, dashboard-below-dams, dam-detail)
- Note each ad unit's slot ID (10 digits)

### 2. Replace placeholder IDs in templates
In all three templates (dashboard.html, dam_detail.html), replace:
  data-ad-client="ca-pub-XXXXXXXXXXXXXXXXXX"   → your publisher ID
  data-ad-slot="XXXXXXXXXX"                    → each unit's slot ID

In base.html cookie consent banner, replace:
  ?client=ca-pub-XXXXXXXXXXXXXXXXXX            → your publisher ID

### 3. Upgrade CSP to Approach B (nonce-based)
In app/security.py:
- Generate a per-request nonce: `base64.b64encode(secrets.token_bytes(16)).decode()`
- Store it: `request.state.csp_nonce = nonce`
- Uncomment _CSP_WITH_ADS and use it instead of _CSP
- Add nonce="{{ request.state.csp_nonce }}" to all <script> and <style> tags in base.html

### 4. Switch CSP from Report-Only to enforcement
In app/security.py, change:
  `Content-Security-Policy-Report-Only` → `Content-Security-Policy`

### 5. Deploy and verify
- systemctl restart waterlevels
- Check browser console: no CSP errors
- Check AdSense dashboard: impressions appear within 24–48h
- Confirm ads render on pages (they may show placeholder for first 24h)
