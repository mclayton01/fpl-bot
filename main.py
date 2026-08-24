"""
Main Entrypoint for Automated FPL Bot.
"""
import sys
import logging
from datetime import datetime, timezone

from config import (
    FPL_TEAM_ID,
    FPL_COOKIE,
    DRY_RUN,
    FORCE_RUN,
    HOURS_BEFORE_DEADLINE,
    MIN_TRANSFER_IMPROVEMENT,
    MAX_TRANSFERS
)
from fpl_api import FPLClient
from optimizer import FPLOptimizer
from notifier import generate_markdown_summary, save_step_summary, send_email_notification

# Configure Rich Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("FPLBot")

def run():
    print("\n" + "="*65)
    print(" 🤖  FPL AUTOMATED HANDS-OFF BOT  ⚽")
    print("="*65)
    print(f"• Target Team ID    : {FPL_TEAM_ID}")
    print(f"• Execution Mode    : {'🔍 DRY RUN (Simulation)' if DRY_RUN else '⚡ LIVE MODE (Submits to FPL)'}")
    print(f"• Force Run Enabled : {FORCE_RUN}")
    print(f"• Deadline Window   : Within {HOURS_BEFORE_DEADLINE} hours")
    print("="*65 + "\n")

    client = FPLClient(team_id=FPL_TEAM_ID, auth_token=FPL_COOKIE)

    # 1. Fetch Core Game Data
    logger.info("Fetching FPL live game state and player statistics...")
    try:
        bootstrap = client.get_bootstrap()
    except Exception as e:
        logger.error(f"Failed to fetch bootstrap static data: {e}")
        sys.exit(1)

    # 2. Check Upcoming Gameweek & Deadline
    next_event, deadline = client.get_next_event(bootstrap)
    now = datetime.now(timezone.utc)
    time_to_deadline = deadline - now
    hours_left = time_to_deadline.total_seconds() / 3600.0
    gw_name = next_event.get("name", "Next Gameweek")
    deadline_str = deadline.strftime("%Y-%m-%d %H:%M UTC")

    print(f"📅 Next Event   : {gw_name}")
    print(f"⏰ Deadline     : {deadline_str} ({hours_left:.1f} hours from now)")

    if hours_left < 0:
        logger.warning("Gameweek deadline has already passed! Waiting for next round to open.")
        return

    # Check if we should execute or wait closer to deadline
    if hours_left > HOURS_BEFORE_DEADLINE and not FORCE_RUN:
        logger.info(f"Deadline is in {hours_left:.1f} hours (> {HOURS_BEFORE_DEADLINE}h).")
        logger.info("Bot will wait until closer to the deadline to ensure the latest team news and press conferences are published.")
        return

    # 3. Fetch Current Squad
    logger.info("Retrieving team picks and squad data...")
    try:
        picks, summary = client.get_current_picks(bootstrap)
    except Exception as e:
        logger.error(f"Failed to fetch current picks: {e}")
        sys.exit(1)

    bank = summary.get("bank", 0)
    free_transfers = summary.get("free_transfers", 1)
    print(f"💰 Available Bank : £{bank / 10:.1f}m")
    print(f"🔄 Free Transfers : {free_transfers}")
    print(f"🔐 Authentication : {'Verified (Session Cookie active)' if summary.get('authenticated') else 'Public Access (Read-Only)'}")
    print("-" * 65)

    # 4. Evaluate Current Squad
    optimizer = FPLOptimizer(bootstrap)
    squad_valuations = []
    for p in picks:
        val = optimizer.evaluate_player(
            element_id=p["element"],
            selling_price=p.get("selling_price"),
            purchase_price=p.get("purchase_price")
        )
        squad_valuations.append(val)

    # Print Current Squad Status
    print("\n📋 Current Squad Status:")
    for val in squad_valuations:
        pos = val.element_type["singular_name_short"]
        name = val.element["web_name"]
        club = val.team["short_name"]
        cost = f"£{val.selling_price / 10:.1f}m"
        ev = f"EV: {max(val.expected_value, 0.0):.2f}"
        flag = f" ⚠️ {val.status_summary}" if val.is_injured_or_flagged else ""
        print(f"  • [{pos:3}] {name:16} ({club:3}) {cost:7} | {ev:8}{flag}")

    # 5. Check for Transfers
    print("\n" + "-" * 65)
    print("🔄 Transfer Analysis:")
    best_transfer = None
    if free_transfers >= 1:
        best_transfer = optimizer.optimize_transfers(
            squad_valuations=squad_valuations,
            bank=bank,
            free_transfers=min(free_transfers, MAX_TRANSFERS),
            min_improvement=MIN_TRANSFER_IMPROVEMENT
        )

    if best_transfer:
        out_p = best_transfer["player_out"]
        in_p = best_transfer["player_in"]
        print(f"  ✨ RECOMMENDED TRANSFER:")
        print(f"     OUT 🔴 : {out_p.element['web_name']} ({out_p.team['short_name']}) - £{out_p.selling_price/10:.1f}m [EV: {max(out_p.expected_value, 0.0):.2f}]")
        print(f"     IN  🟢 : {in_p.element['web_name']} ({in_p.team['short_name']}) - £{in_p.element['now_cost']/10:.1f}m [EV: {in_p.expected_value:.2f}]")
        print(f"     GAIN   : +{best_transfer['gain']:.2f} Expected Points (Cost: 0 pts)")

        if not DRY_RUN:
            logger.info("Submitting transfer to FPL API...")
            transfer_payload = [{
                "element_in": in_p.element["id"],
                "element_out": out_p.element["id"],
                "purchase_price": best_transfer["purchase_price"],
                "selling_price": best_transfer["selling_price"]
            }]
            success = client.execute_transfers(transfer_payload, next_event["id"])
            if success:
                squad_valuations = [p for p in squad_valuations if p.element["id"] != out_p.element["id"]] + [in_p]
            else:
                logger.warning("Transfer submission failed. Keeping existing squad for lineup optimization.")
        else:
            logger.info("[DRY RUN] Transfer simulated. Applying target to simulated lineup.")
            squad_valuations = [p for p in squad_valuations if p.element["id"] != out_p.element["id"]] + [in_p]
    else:
        print("  ✅ Squad is optimal or no transfer exceeded improvement threshold. Rolling free transfer!")

    # 6. Optimize Lineup, Bench & Captaincy
    print("\n" + "-" * 65)
    print("⚽ Optimal Lineup & Captaincy:")
    final_picks, formation, captain, vice_captain = optimizer.optimize_lineup(squad_valuations)

    print(f"  • Formation: {formation[0]}-{formation[1]}-{formation[2]}")
    print(f"  • Captain   : {captain.element['web_name']} (C) - Expected Value: {captain.expected_value:.2f}")
    print(f"  • Vice-Cap  : {vice_captain.element['web_name']} (VC) - Expected Value: {vice_captain.expected_value:.2f}")

    print("\n  🛡️  STARTING XI:")
    for p in final_picks[:11]:
        val = p["valuation"]
        cap_badge = " (C) 👑" if p["is_captain"] else (" (VC) 🥈" if p["is_vice_captain"] else "")
        print(f"    [{p['position']:2}] {val.element_type['singular_name_short']:3} {val.element['web_name']:15} ({val.team['short_name']}) | EV: {val.expected_value:.2f}{cap_badge}")

    print("\n  🪑  BENCH ORDER (Auto-sub priority):")
    for p in final_picks[11:]:
        val = p["valuation"]
        bench_num = p['position'] - 11
        bench_role = "GK Sub" if bench_num == 1 else f"Sub {bench_num - 1}"
        print(f"    [{bench_role:7}] {val.element_type['singular_name_short']:3} {val.element['web_name']:15} ({val.team['short_name']}) | EV: {max(val.expected_value, 0.0):.2f}")

    # 7. Submit Lineup if Live
    if not DRY_RUN:
        logger.info("Submitting optimal lineup and captaincy to FPL API...")
        api_picks = [{
            "element": p["element"],
            "position": p["position"],
            "is_captain": p["is_captain"],
            "is_vice_captain": p["is_vice_captain"]
        } for p in final_picks]
        client.update_lineup(api_picks)
    else:
        logger.info("[DRY RUN] Lineup optimization completed successfully (No live changes sent).")

    # 8. Generate and Publish Rich Markdown Summary & Notifications
    md_summary = generate_markdown_summary(
        team_id=FPL_TEAM_ID,
        gameweek_name=gw_name,
        deadline_str=deadline_str,
        is_dry_run=DRY_RUN,
        summary_data=summary,
        squad_valuations=squad_valuations,
        best_transfer=best_transfer,
        final_picks=final_picks,
        formation=formation,
        captain=captain,
        vice_captain=vice_captain
    )
    save_step_summary(md_summary)

    print("\n" + "="*65)
    print(" 🎉  FPL BOT RUN COMPLETE!  🚀")
    print("="*65 + "\n")

if __name__ == "__main__":
    run()
