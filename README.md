# ⚽ Automated Fantasy Premier League (FPL) Bot

A 100% hands-off, automated Fantasy Premier League bot designed to manage your team throughout the season using **GitHub Actions**.

---

## 🌟 What This Bot Does Every Gameweek

```
[⏰ 6 Hours Before Deadline]
        │
        ├── 1. 🏥 Checks Injury Reports & Flagged Players
        ├── 2. 🔄 Finds Best Free Transfer (Upgrades weak links within budget)
        ├── 3. 🛡️ Solves Optimal Starting XI & Formation (e.g. 3-5-2, 3-4-3)
        ├── 4. 🪑 Prioritizes Bench Order (Auto-subs best backup if starter is benched)
        ├── 5. 👑 Picks Captain (C) & Vice-Captain (VC)
        ├── 6. 🚀 Submits Changes Directly to FPL
        ├── 7. 📊 Publishes Visual Summary Card to GitHub
        └── 8. 📧 Sends Matchday Preview Email to your inbox
```

---

## 📊 Where to View Your Weekly Visual Report
1. Go to your repository's **[Actions](https://github.com/mclayton01/fpl-bot/actions)** tab.
2. Click on the latest run (e.g. `FPL Automated Gameweek Manager`).
3. Scroll down on the **Summary** page to see your complete visual matchday table!

---

## 💡 How to Refresh Your Token in 10 Seconds
If FPL ever forces a logout during the season, you can refresh your token in 10 seconds:

1. Open [fantasy.premierleague.com](https://fantasy.premierleague.com/) in your browser while logged in.
2. Press `F12` (or Right-Click $\rightarrow$ **Inspect**) and click the **Console** tab.
3. Paste this exact 1-line command and press **Enter**:
   ```javascript
   copy(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('oidc.user'))))
   ```
4. Go to **[GitHub Secrets](https://github.com/mclayton01/fpl-bot/settings/secrets/actions)** $\rightarrow$ click **`FPL_COOKIE`** $\rightarrow$ paste and save!

---

## 📧 How to Enable Email Notifications
To receive weekly match preview emails in your inbox (`markjclayton@gmail.com`):
1. Generate a 16-character Google App Password at: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. In your GitHub repository **[Secrets](https://github.com/mclayton01/fpl-bot/settings/secrets/actions)**, add:
   * **Name**: `SMTP_PASS`
   * **Value**: *(Your 16-character Google App Password)*
