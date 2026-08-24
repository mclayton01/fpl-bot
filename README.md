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
        └── 6. 🚀 Submits Changes Directly to FPL
```

---

## 🚀 Quick Setup Guide (5 Minutes)

### Step 1: Create a Private GitHub Repository
1. Go to [GitHub.com/new](https://github.com/new).
2. Name your repo (e.g. `fpl-bot`).
3. Set visibility to **Private** (to protect your settings).
4. Click **Create repository**.

---

### Step 2: Get Your FPL Session Cookie (`pl_profile`)
Because the FPL login page uses anti-bot verification, the bot uses your browser's active session token instead of storing your password.

1. Open Chrome (or any browser) and log in to [fantasy.premierleague.com](https://fantasy.premierleague.com/).
2. Press `F12` (or Right-Click anywhere $\rightarrow$ **Inspect**) to open Developer Tools.
3. Click the **Application** tab at the top (in Firefox/Safari, it is called **Storage**).
4. In the left sidebar, expand **Cookies** $\rightarrow$ click `https://fantasy.premierleague.com`.
5. Find the row named **`pl_profile`** and copy its **Value** (a long string of letters/numbers).

---

### Step 3: Add Your Secrets in GitHub
1. In your GitHub repository, go to **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
2. Click **New repository secret**.
3. Add these two secrets:
   * **Name**: `FPL_COOKIE`  
     **Value**: *(Paste the `pl_profile` value you copied)*
   * **Name**: `FPL_TEAM_ID`  
     **Value**: `8662144`

---

### Step 4: Push the Bot Code to GitHub
Run these commands in your terminal to push this project to your new private GitHub repository:

```bash
cd /usr/local/google/home/markclayton/.gemini/jetski/scratch/fpl-bot
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/fpl-bot.git
git branch -M main
git push -u origin main
```

---

## 🎮 How to Test or Run Manually

1. Go to the **Actions** tab in your GitHub repository.
2. Select **FPL Automated Gameweek Manager** in the left sidebar.
3. Click **Run workflow** $\rightarrow$ choose whether you want **Dry Run** or **Live Run** $\rightarrow$ click the green **Run workflow** button!

The bot will execute in the cloud, print a complete breakdown of your squad, and update your team!
