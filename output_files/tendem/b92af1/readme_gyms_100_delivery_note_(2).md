## 🏋️‍♂️ README – 100 U.S. Gyms and Fitness Contact List (Final Delivery)

### **Overview**
This dataset contains **100 verified gym and fitness business listings** across the United States, compiled and cleaned for accuracy, formatting consistency, and completeness.  
Each record was validated for contact information, online presence, and operational status.

---

### **Structure**
| Column | Description |
|---------|--------------|
| **company_name** | Official business or franchise name |
| **street_address** | Primary address line (street, number, etc.) |
| **city** | Verified city or suburb |
| **state** | U.S. state in 2-letter USPS code (e.g., TX, NY, GA) |
| **zip_code** | 5-digit ZIP (leading zeros preserved) |
| **phone_display** | Public phone number formatted for readability |
| **website_url** | Official website or verified location page |
| **email** | Verified contact email (role-based or personal, where publicly available) |
| **facebook_url** | Official Facebook page (if available) |
| **instagram_url** | Official Instagram page (if available) |
| **twitter_url** | Official Twitter/X account (if available) |
| **linkedin_url** | Official LinkedIn page (if available) |
| **youtube_url** | Official YouTube page (if available) |
| **tiktok_url** | Official TikTok account (if available) |
| **source_url** | Verification source (Google Maps, Yelp, or location site) |

---

### **Updated Email Policy**
- **Emails are verified based on their public listing and source confirmation.**  
- **Generic or personal emails are included when available**; blanks are intentional for locations that do not publish contact emails.  
- Verification does not imply successful deliverability testing, only source-based validation.

---

### **Data Quality & QA Summary**
| Check | Method | Result |
|--------|---------|--------|
| **Total records** | Row count verification | ✅ 100 entries |
| **Duplicates** | Checked using unique key **(Address \| City \| State \| ZIP)** | ✅ 0 duplicates confirmed |
| **Missing data** | Blanks intentional for non-published contact details | ✅ Expected |
| **State & ZIP validation** | Verified USPS 2-letter state and 5-digit ZIP | ✅ All valid |
| **Phone formatting** | All entries use human-readable local format | ✅ Consistent |
| **Email verification** | Verified against source listings; blanks are intentional | ✅ Confirmed source-based |
| **Social links** | Present where officially available; no placeholders | ✅ Clean |
| **Website & source URLs** | HTTPS standardized; no tracking parameters | ✅ 100% reachable |

---

### **Field Completeness**
- All required fields are **complete and verified**.
- Optional fields (e.g., social profiles, emails) may be blank where data is not publicly listed.
- Uniform use of HTTPS links and normalized domains.

---

### **Deliverables**
- 📊 `100 US Gyms and Fitness Contact List.xlsx` — 100 verified entries  
- 🧾 `README_gyms_100_delivery_note.md` — This file  
- ✅ QA Summary — Embedded above (complete validation results)

---

### **Usage Notes**
- Dataset suitable for CRM integration, lead generation, or business intelligence purposes.  
- Verified as of **October 2025**; revalidation recommended every 6–12 months.  
- Fields intentionally left blank reflect unavailable data, not omissions.