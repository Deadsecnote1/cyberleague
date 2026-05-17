# Demo video script (~3 minutes)

**Title:** Cyber League — n8n Bug Bounty Pipeline | Hackers League | Cursor Buildathon  
**Format:** YouTube unlisted  
**Record:** 1080p, show n8n + portal side by side or cut between them

**Demo URL:** https://youtu.be/d1xiZMBJ61k (linked in README and submission doc).

---

## 0:00–0:20 — Hook

**Say:**  
"This is Cyber League by Hackers League — an n8n-powered bug bounty pipeline. The portal is only the control plane; **n8n orchestrates every scan**, runs the tools, and produces reports. We only test authorized targets."

**Show:** Portal dashboard logo, quick glimpse of n8n workflow canvas (zoomed out).

---

## 0:20–0:45 — Problem & architecture

**Say:**  
"Manual recon is fragmented — subdomains, headers, nuclei, SQLi, all in different tabs. We unified it in one workflow with scope controls and rate-limit protection."

**Show:** Simple diagram or README architecture section.

**On screen text (optional):** Portal → n8n webhook → bugbounty-scan.sh → scans/ + reports/

---

## 0:45–1:30 — Launch scan (portal)

**Say:**  
"I'll scan a deliberately vulnerable lab — testphp.vulnweb.com — with Quick preset."

**Do:**

1. Open http://127.0.0.1:8765/scan  
2. Target: `http://testphp.vulnweb.com`  
3. Load scope template **Acunetix Vulnweb** (or enter `testphp.vulnweb.com` + `*.vulnweb.com`)  
4. Preset: **Quick**  
5. Enable **SQL injection checks** and **AI hunt advisor**  
6. Click **Start scan**

**Show:** Success message; mention webhook fired to n8n.

---

## 1:30–2:10 — n8n engine

**Say:**  
"Under the hood, n8n receives the portal webhook, parses scope and config, optionally runs AI pre-scan, then Execute Command runs our worker script."

**Do:**

1. Open n8n → **Executions** — show running/completed execution  
2. Open workflow: highlight **Portal Scan (webhook)** → **Parse Portal Request** → **Run Pentest Tools**  
3. Briefly show execution log / command node output if available  

---

## 2:10–2:40 — Results

**Say:**  
"Artifacts land under scans/ with vulnerabilities.json. The portal shows findings by severity; we can open HTML reports and AI post-scan notes."

**Do:**

1. Portal → Dashboard → **View** latest run  
2. Show scope section, findings table, host list  
3. Open a report under **Reports** or `reports/bugbounty-report-*.html`  
4. Show `reports/ai_pre_scan.md` or post-scan if AI ran  

**Call out:** SQLi findings (if any) under injection category.

---

## 2:40–3:00 — Safety & close

**Say:**  
"Scope is enforced before and during the scan. Rate-limit guard can stop if the target blocks us. Stack is Linux-first, local-only, built with Cursor for the n8n track. Code and submission doc are on GitHub — Hackers League, Cyber League."

**Show:**  
- `cyberleague.sh` / `./shutdown.sh` one-liner  
- README repo link: https://github.com/Deadsecnote1/cyberleague  

---

## Recording checklist

- [ ] `./cyberleague.sh` running; n8n workflow **Active**  
- [ ] `config/openai.env` set for AI segment (or mention graceful skip)  
- [ ] No real customer domains in video  
- [x] Unlisted YouTube link added to README + `docs/CURSOR_BUILDATHON_SUBMISSION.md`  
- [ ] Audio clear; cursor highlights clicks  

## Suggested vulnerable targets

| URL | Notes |
|-----|--------|
| http://testphp.vulnweb.com | Reliable for SQLi demo (`artists.php?artist=1`) |
| https://demo.testfire.net | Banking demo app |
| https://juice-shop.herokuapp.com | Popular OWASP app (may be slower) |
