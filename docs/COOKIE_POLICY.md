# Cookie Policy / Cookie-Richtlinie

**LIARA - Digital Companion**  
**Version:** 3.0.0  
**Last Updated:** December 6, 2025  
**Compliance:** EU ePrivacy Directive, GDPR, UK GDPR, CCPA

---

## 🍪 What Are Cookies?

Cookies are small text files stored on your device (computer, phone, tablet) when you visit a website. They allow the website to remember your preferences and actions.

**LIARA uses minimal, essential cookies only.** We do **NOT** use:
- ❌ Advertising cookies
- ❌ Tracking cookies
- ❌ Third-party analytics cookies
- ❌ Social media cookies

---

## 📋 Cookies We Use

### Essential Cookies (Always Active)

These cookies are **strictly necessary** for LIARA to function. They cannot be disabled.

| Cookie Name | Purpose | Duration | Category |
|-------------|---------|----------|----------|
| `access_token` | Authentication (JWT) | 1 hour | Essential |
| `refresh_token` | Session renewal | 7 days | Essential |
| `liara-theme` | Theme preference (dark/light) | 1 year | Essential |
| `liara-language` | Language preference | 1 year | Essential |
| `liara-consent` | Privacy consent status | 1 year | Essential |

**Legal Basis:** These cookies are necessary for the performance of the service (GDPR Art. 6(1)(b) - Contract performance).

**No consent required** under EU ePrivacy Directive (strictly necessary cookies are exempt).

---

## 🎯 What We Do NOT Use

### No Third-Party Cookies

LIARA does **NOT** set cookies from:
- ❌ Google Analytics
- ❌ Facebook Pixel
- ❌ Advertising networks
- ❌ Social media platforms
- ❌ Any third-party tracking services

### No Cross-Site Tracking

LIARA does **NOT**:
- ❌ Track your browsing across other websites
- ❌ Build user profiles for advertising
- ❌ Share cookie data with third parties

---

## 🔒 Session Storage and Local Storage

In addition to cookies, LIARA uses **browser storage** for:

### Local Storage (Permanent Until Cleared)

| Key | Purpose | Data Stored |
|-----|---------|-------------|
| `liara-theme` | Theme preference backup | `"dark"` or `"light"` |
| `liara-settings` | User UI preferences | JSON object (sidebar state, etc.) |
| `liara-chat-draft` | Draft messages | Unfinished chat input |

**Legal Basis:** Consent (GDPR Art. 6(1)(a)) - by using LIARA, you consent to local storage.

### Session Storage (Cleared When Browser Closes)

| Key | Purpose | Data Stored |
|-----|---------|-------------|
| `liara-active-chat` | Current chat session ID | UUID |
| `liara-scroll-position` | UI state | Scroll position |

**Legal Basis:** Legitimate interest (GDPR Art. 6(1)(f)) - necessary for smooth user experience.

---

## 🛠️ How to Manage Cookies

### Clearing Cookies in LIARA

**Option 1: Logout**
- Click "Logout" in LIARA
- This clears `access_token` and `refresh_token`
- Theme and language preferences remain

**Option 2: Privacy Settings**
- Go to **Settings > Privacy Settings**
- Click "Clear All Cookies and Cache"
- This removes all cookies and local storage

### Clearing Cookies in Your Browser

#### Google Chrome
1. Settings → Privacy and Security → Cookies and other site data
2. See all site data and permissions
3. Find your LIARA domain (e.g., `localhost:8100`)
4. Click "Remove"

#### Mozilla Firefox
1. Settings → Privacy & Security → Cookies and Site Data
2. Manage Data
3. Find your LIARA domain
4. Remove Selected

#### Safari
1. Preferences → Privacy → Manage Website Data
2. Find your LIARA domain
3. Remove

#### Microsoft Edge
1. Settings → Cookies and site permissions → Cookies and site data
2. See all cookies and site data
3. Find your LIARA domain
4. Remove

### Disabling Cookies Entirely

⚠️ **Warning:** Disabling cookies will **break LIARA's functionality**. You will not be able to:
- Log in
- Maintain sessions
- Save preferences

**To disable cookies:**
- Browser Settings → Privacy → Block all cookies
- (Not recommended for LIARA)

---

## 🌍 International Compliance

### EU ePrivacy Directive

**Strictly Necessary Cookies Exemption:**
LIARA's cookies are exempt from the consent requirement under the ePrivacy Directive because they are "strictly necessary for the provision of an information society service explicitly requested by the subscriber or user."

**No cookie banner required** for essential cookies only.

### UK GDPR / PECR

Same as EU ePrivacy - essential cookies do not require consent.

**ICO Guidance:** "Strictly necessary cookies do not require consent."

### CCPA (California)

**Do Not Sell My Personal Information:**
LIARA does **NOT** sell cookie data or any personal information.

**Third-Party Cookies:**
LIARA does **NOT** use third-party cookies.

**Compliance:** ✅ CCPA-friendly (no data sales, no tracking)

### Canada (PIPEDA)

**Consent Requirement:**
LIARA's cookies are considered "implied consent" - by using the service, you consent to essential cookies.

**Opt-Out:**
You can clear cookies at any time (see above).

---

## 🔍 Cookie Audit

### Last Audit: December 6, 2025

**Cookies Found:** 5  
**Third-Party Cookies:** 0  
**Tracking Cookies:** 0  
**Advertising Cookies:** 0  

**Result:** ✅ **100% Essential Cookies Only**

---

## 📊 Cookie Comparison

| Feature | LIARA | Typical Website |
|---------|-------|-----------------|
| **Total Cookies** | 5 | 20-100+ |
| **Third-Party Cookies** | 0 | 10-50 |
| **Tracking Cookies** | 0 | Yes (Google Analytics, etc.) |
| **Advertising Cookies** | 0 | Yes (Google Ads, Facebook, etc.) |
| **Cookie Banner Needed** | ❌ No | ✅ Yes |
| **GDPR Consent Needed** | ❌ No (essential only) | ✅ Yes |
| **Data Sales** | ❌ Never | Often |

---

## 🛡️ Privacy-First Cookie Design

### Principles

LIARA follows **Privacy by Design** for cookies:

1. **Minimal Use**: Only essential cookies, no extras
2. **No Third Parties**: All cookies set by LIARA, none by external services
3. **No Tracking**: No behavioral tracking or profiling
4. **Transparency**: This policy documents all cookies
5. **User Control**: Easy to clear cookies at any time
6. **Secure**: Cookies use `Secure` and `HttpOnly` flags (where applicable)

### Cookie Attributes

**Security Flags:**
```http
Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Strict
```

- ✅ **HttpOnly**: Prevents JavaScript access (XSS protection)
- ✅ **Secure**: Only sent over HTTPS
- ✅ **SameSite=Strict**: Prevents CSRF attacks

---

## 🆘 Questions About Cookies?

### Common Questions

**Q: Why do you need cookies at all?**  
A: Cookies are essential for authentication. Without them, you'd have to log in on every page load.

**Q: Do you track me across websites?**  
A: No. LIARA's cookies only work on your LIARA instance. They are not shared with other sites.

**Q: Can I use LIARA without cookies?**  
A: No. Cookies are strictly necessary for basic functionality (login, sessions, preferences).

**Q: Do you use cookie banners?**  
A: No. Since LIARA only uses essential cookies, no consent banner is required under EU law.

**Q: What happens if I clear cookies?**  
A: You'll be logged out and preferences will reset. Your data (chats, tasks, etc.) remains safe in the database.

---

## 📞 Contact

For questions about cookies or privacy:

**Instance Operator:**  
[Your Name/Organization]  
[Your Email]

**LIARA Project:**  
GitHub: https://github.com/[your-repo]  
Privacy Discussions: https://github.com/[your-repo]/discussions

---

## 📋 Summary

| Aspect | Status |
|--------|--------|
| **Total Cookies** | 5 (all essential) |
| **Third-Party Cookies** | ❌ None |
| **Tracking Cookies** | ❌ None |
| **Advertising Cookies** | ❌ None |
| **GDPR Compliance** | ✅ Essential cookies only |
| **CCPA Compliance** | ✅ No data sales |
| **Cookie Banner Required** | ❌ No (essential only) |
| **User Control** | ✅ Clear cookies anytime |

---

## 🔄 Updates to This Policy

This Cookie Policy was last updated on **December 6, 2025**.

Changes will be communicated via:
- In-app notification
- GitHub release notes
- Email (if applicable)

Continued use after changes = acceptance of updated policy.

---

**Version:** 3.0.0  
**Last Updated:** December 6, 2025  
**Next Review:** December 2026

**Related Documents:**
- International Privacy Policy (INTERNATIONAL_PRIVACY_POLICY.md)
- Terms of Service (TERMS_OF_SERVICE.md)
- AI Transparency Statement (AI_TRANSPARENCY_STATEMENT.md)

---

**🍪 LIARA: Privacy-First Cookies • No Tracking • No Third Parties • 100% Essential**
