"""
Notification engine: Generates GitHub Actions Step Summaries, HTML Emails with built-in click guides.
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
    best_transfers: list,
    final_picks: list,
    formation: tuple,
    captain,
    vice_captain
) -> str:
    """Generates rich GitHub Flavored Markdown for the GitHub Actions Step Summary."""
    md = []
    md.append(f"# ⚽ FPL Manager Cheat Sheet: {gameweek_name}")
    md.append(f"> **Team ID:** `{team_id}` | **Deadline:** `{deadline_str}`\n")
    
    # 1. Transfers Section
    md.append(f"## 🔄 Recommended Transfers ({len(best_transfers)})")
    if best_transfers:
        md.append("| Action | Player | Club | Position | Cost | Expected Points |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        total_gain = 0.0
        for tr in best_transfers:
            out_p = tr["player_out"]
            in_p = tr["player_in"]
            total_gain += tr["gain"]
            md.append(f"| 🔴 **OUT** | {out_p.element['web_name']} | {out_p.team['short_name']} | {out_p.element_type['singular_name_short']} | £{out_p.selling_price/10:.1f}m | {max(out_p.expected_value, 0.0):.2f} |")
            md.append(f"| 🟢 **IN** | **{in_p.element['web_name']}** | {in_p.team['short_name']} | {in_p.element_type['singular_name_short']} | £{in_p.element['now_cost']/10:.1f}m | **{in_p.expected_value:.2f}** |")
        md.append(f"\n✨ **Total Expected Gain:** `+{total_gain:.2f} points` (Cost: 0 pts)\n")
    else:
        md.append("✅ **Squad is optimal!** No transfer needed this week.\n")

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
        role_desc = "1st Auto-Sub if starter benched" if b_idx == 2 else "Backup"
        md.append(f"| {slot_name} | {val.element['web_name']} | {val.team['short_name']} | {val.element_type['singular_name_short']} | {max(val.expected_value, 0.0):.2f} | {role_desc} |")

    md.append("\n---\n*Automated with ❤️ by your FPL Assistant*")
    return "\n".join(md)

def generate_html_email(
    team_id: int,
    gameweek_name: str,
    deadline_str: str,
    is_dry_run: bool,
    summary_data: dict,
    best_transfers: list,
    final_picks: list,
    formation: tuple,
    captain,
    vice_captain
) -> str:
    """Generates a clean, friendly HTML email with exact desktop click instructions."""
    transfer_html = ""
    transfer_guide_steps = ""
    
    if best_transfers:
        transfer_cards = ""
        total_gain = 0.0
        for i, tr in enumerate(best_transfers, 1):
            out_p = tr["player_out"]
            in_p = tr["player_in"]
            total_gain += tr["gain"]
            transfer_cards += f"""
            <div style="margin-top:8px;padding-top:8px;border-top:1px solid #2a2a3c;">
                <p style="margin:3px 0;color:#ff4d4d;font-size:14px;">🔴 <b>OUT:</b> {out_p.element['web_name']} ({out_p.team['short_name']}) - £{out_p.selling_price/10:.1f}m</p>
                <p style="margin:3px 0;color:#00ff87;font-size:14px;">🟢 <b>IN:</b> {in_p.element['web_name']} ({in_p.team['short_name']}) - £{in_p.element['now_cost']/10:.1f}m</p>
            </div>
            """
            transfer_guide_steps += f"<li>Click <b>Transfers</b> tab &rarr; Click <b>{out_p.element['web_name']}</b> &rarr; Click red <b>X</b> &rarr; Search & Add <b>{in_p.element['web_name']}</b>.</li>"
        
        transfer_html = f"""
        <div style="background:#1f1f2e;border-radius:12px;padding:16px;margin-bottom:20px;border-left:4px solid #00ff87;">
            <h3 style="margin:0;color:#ffffff;font-size:16px;">🔄 Recommended Free Transfers ({len(best_transfers)})</h3>
            {transfer_cards}
            <p style="margin:10px 0 0 0;color:#38ef7d;font-size:13px;font-weight:bold;">✨ Net Gain: +{total_gain:.2f} Expected Points (Cost: 0 pts)</p>
        </div>
        """
    else:
        transfer_html = """
        <div style="background:#1f1f2e;border-radius:12px;padding:14px;margin-bottom:20px;border-left:4px solid #00d2ff;">
            <p style="margin:0;color:#ffffff;font-size:14px;">✅ <b>Squad is Optimal:</b> No transfer needed this week. Free transfer rolled for next week!</p>
        </div>
        """
        transfer_guide_steps = "<li>No transfers needed this week!</li>"

    starters_rows = ""
    for p in final_picks[:11]:
        val = p["valuation"]
        badge = "👑 <b>(C)</b>" if p["is_captain"] else ("🥈 (VC)" if p["is_vice_captain"] else "")
        starters_rows += f"""
        <tr style="border-bottom:1px solid #2a2a3c;">
            <td style="padding:10px 8px;color:#a0a0b0;font-size:13px;">{val.element_type['singular_name_short']}</td>
            <td style="padding:10px 8px;color:#ffffff;font-size:14px;font-weight:600;">{val.element['web_name']} <span style="color:#00ff87;">{badge}</span></td>
            <td style="padding:10px 8px;color:#a0a0b0;font-size:13px;">{val.team['short_name']}</td>
            <td style="padding:10px 8px;color:#38ef7d;font-size:13px;font-weight:bold;text-align:right;">{val.expected_value:.2f}</td>
        </tr>
        """

    bench_rows = ""
    for p in final_picks[11:]:
        val = p["valuation"]
        b_idx = p["position"] - 11
        slot = "GK Sub" if b_idx == 1 else f"Sub #{b_idx - 1}"
        bench_rows += f"""
        <tr style="border-bottom:1px solid #2a2a3c;">
            <td style="padding:8px;color:#808090;font-size:12px;">{slot}</td>
            <td style="padding:8px;color:#d0d0e0;font-size:13px;">{val.element['web_name']} ({val.element_type['singular_name_short']})</td>
            <td style="padding:8px;color:#808090;font-size:12px;">{val.team['short_name']}</td>
            <td style="padding:8px;color:#a0a0b0;font-size:12px;text-align:right;">{max(val.expected_value, 0.0):.2f}</td>
        </tr>
        """

    cap_name = captain.element['web_name']
    vc_name = vice_captain.element['web_name']

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:20px;background:#0d0d17;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#ffffff;">
        <div style="max-width:580px;margin:0 auto;background:#151522;border-radius:16px;overflow:hidden;border:1px solid #28283d;">
            
            <!-- Header -->
            <div style="background:linear-gradient(135deg, #37003c 0%, #11001a 100%);padding:24px;border-bottom:2px solid #00ff87;">
                <h1 style="margin:0;font-size:22px;color:#00ff87;letter-spacing:0.5px;">⚽ Your FPL Matchday Cheat Sheet</h1>
                <p style="margin:6px 0 0 0;color:#d0d0e0;font-size:14px;">{gameweek_name} &bull; Deadline: <b>{deadline_str}</b></p>
            </div>

            <div style="padding:20px;">
                
                <!-- Quick 30-Sec Action Guide -->
                <div style="background:#1b2838;border-radius:12px;padding:16px;margin-bottom:20px;border:1px solid #2d4460;">
                    <h3 style="margin:0 0 10px 0;color:#00d2ff;font-size:15px;">📋 30-Second Desktop Click-Guide</h3>
                    <ol style="margin:0;padding-left:20px;color:#e0e0f0;font-size:13px;line-height:1.7;">
                        {transfer_guide_steps}
                        <li>Click <b>Confirm Transfers</b> (green button).</li>
                        <li>Click <b>Pick Team</b> tab &rarr; Click <b>{cap_name}</b> &rarr; Click <b>Make Captain 👑</b>.</li>
                        <li>Click <b>Save Your Team</b>. Done!</li>
                    </ol>
                </div>

                <!-- Transfer Box -->
                {transfer_html}

                <!-- Captain Summary -->
                <div style="background:#1f1f2e;border-radius:12px;padding:14px;margin-bottom:20px;display:flex;justify-content:space-between;">
                    <div>👑 <b>Captain (2x Points):</b> <span style="color:#00ff87;font-weight:bold;">{cap_name}</span></div>
                    <div>🥈 <b>Vice-Captain:</b> <span style="color:#ffffff;">{vc_name}</span></div>
                </div>

                <!-- Starting XI -->
                <h3 style="margin:16px 0 8px 0;color:#ffffff;font-size:15px;letter-spacing:0.5px;">🛡️ STARTING XI ({formation[0]}-{formation[1]}-{formation[2]})</h3>
                <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
                    {starters_rows}
                </table>

                <!-- Bench -->
                <h3 style="margin:16px 0 8px 0;color:#a0a0b0;font-size:14px;letter-spacing:0.5px;">🪑 BENCH (AUTO-SUB ORDER)</h3>
                <table style="width:100%;border-collapse:collapse;margin-bottom:10px;">
                    {bench_rows}
                </table>

            </div>

            <!-- Footer -->
            <div style="background:#0e0e18;padding:14px 20px;text-align:center;font-size:12px;color:#707080;border-top:1px solid #202030;">
                Hands-Off FPL Assistant &bull; Team ID: {team_id}
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_email_notification(subject: str, html_content: str):
    """Sends an HTML email notification if SMTP credentials or Notification Email is configured."""
    recipient = os.getenv("NOTIFICATION_EMAIL", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()

    if not recipient or not smtp_user or not smtp_pass:
        logger.info("Email notification skipped (SMTP credentials not configured).")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"FPL Manager <{smtp_user}>"
        msg["To"] = recipient
        msg["Reply-To"] = smtp_user
        msg["X-Priority"] = "1"
        msg["Priority"] = "Urgent"
        msg["Importance"] = "high"

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())

        logger.info(f"Successfully sent FPL match preview email to {recipient}!")
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
