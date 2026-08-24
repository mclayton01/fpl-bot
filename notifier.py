"""
Notification engine: Generates GitHub Actions Step Summaries, HTML Emails, and Webhooks.
"""
import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("FPLBot")

def generate_markdown_summary(
    team_id: int,
    gameweek_name: str,
    deadline_str: str,
    is_dry_run: bool,
    summary_data: dict,
    squad_valuations: list,
    best_transfer: dict,
    final_picks: list,
    formation: tuple,
    captain,
    vice_captain
) -> str:
    """Generates rich GitHub Flavored Markdown for the GitHub Actions Step Summary."""
    mode_badge = "🔍 **Simulation (Dry Run)**" if is_dry_run else "⚡ **Live Gameweek Submission**"
    
    md = []
    md.append(f"# ⚽ FPL Automated Manager: {gameweek_name}")
    md.append(f"> **Mode:** {mode_badge} | **Team ID:** `{team_id}` | **Deadline:** `{deadline_str}`\n")
    
    # 1. Transfers Section
    md.append("## 🔄 Transfer Activity")
    if best_transfer:
        out_p = best_transfer["player_out"]
        in_p = best_transfer["player_in"]
        md.append("| Action | Player | Club | Position | Cost | Expected Points |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        md.append(f"| 🔴 **OUT** | {out_p.element['web_name']} | {out_p.team['short_name']} | {out_p.element_type['singular_name_short']} | £{out_p.selling_price/10:.1f}m | {max(out_p.expected_value, 0.0):.2f} |")
        md.append(f"| 🟢 **IN** | **{in_p.element['web_name']}** | {in_p.team['short_name']} | {in_p.element_type['singular_name_short']} | £{in_p.element['now_cost']/10:.1f}m | **{in_p.expected_value:.2f}** |")
        md.append(f"\n✨ **Net Expected Gain:** `+{best_transfer['gain']:.2f} points` (Cost: 0 pts)\n")
    else:
        md.append("✅ **Squad is optimal!** No transfer exceeded the improvement threshold. Free transfer rolled for next week.\n")

    # 2. Starting XI Section
    md.append(f"## 🛡️ Starting XI (Formation: {formation[0]}-{formation[1]}-{formation[2]})")
    md.append("| Pos | Role | Player | Club | Form | Expected Points | Status |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for p in final_picks[:11]:
        val = p["valuation"]
        pos_name = val.element_type["singular_name_short"]
        role = "👑 **Captain (2x)**" if p["is_captain"] else ("🥈 **Vice-Cap**" if p["is_vice_captain"] else "Starter")
        name = f"**{val.element['web_name']}**" if p["is_captain"] else val.element['web_name']
        md.append(f"| {p['position']} | {role} | {name} | {val.team['short_name']} | {val.element.get('form', '0.0')} | **{val.expected_value:.2f}** | {val.status_summary} |")

    # 3. Bench Section
    md.append("\n## 🪑 Bench Priority (Auto-Sub Order)")
    md.append("| Bench Slot | Player | Club | Position | Expected Points | Role |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for p in final_picks[11:]:
        val = p["valuation"]
        b_idx = p["position"] - 11
        slot_name = "🧤 **GK Sub**" if b_idx == 1 else f"Sub #{b_idx - 1}"
        md.append(f"| {slot_name} | {val.element['web_name']} | {val.team['short_name']} | {val.element_type['singular_name_short']} | {max(val.expected_value, 0.0):.2f} | 1st Auto-Sub if starter benched |" if b_idx == 2 else f"| {slot_name} | {val.element['web_name']} | {val.team['short_name']} | {val.element_type['singular_name_short']} | {max(val.expected_value, 0.0):.2f} | Backup |")

    md.append("\n---\n*Automated with ❤️ by your FPL Cloud Manager*")
    return "\n".join(md)

def send_email_notification(subject: str, html_content: str):
    """Sends an HTML email notification if SMTP credentials or Notification Email is configured."""
    recipient = os.getenv("NOTIFICATION_EMAIL", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()

    if not recipient or not smtp_user or not smtp_pass:
        logger.info("Email notification skipped (NOTIFICATION_EMAIL or SMTP credentials not configured).")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = recipient

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())

        logger.info(f"Successfully sent FPL update email to {recipient}!")
    except Exception as e:
        logger.warning(f"Could not send email notification: {e}")

def save_step_summary(markdown_text: str):
    """Writes the markdown summary to GitHub Actions Step Summary if running in CI."""
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(markdown_text + "\n")
            logger.info("Published rich Markdown report to GitHub Actions Summary page!")
        except Exception as e:
            logger.warning(f"Could not write to GITHUB_STEP_SUMMARY: {e}")
