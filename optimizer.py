"""
FPL Optimization Engine: Player valuation, Formation solver, Captaincy selector, and Multi-Transfer optimizer.
"""
from dataclasses import dataclass
from typing import Optional

VALID_FORMATIONS = [
    (3, 5, 2),
    (3, 4, 3),
    (4, 4, 2),
    (4, 3, 3),
    (4, 5, 1),
    (5, 3, 2),
    (5, 4, 1),
    (5, 2, 3),
]

@dataclass
class PlayerValuation:
    element: dict
    team: dict
    element_type: dict
    selling_price: int
    purchase_price: int
    expected_value: float
    is_injured_or_flagged: bool
    status_summary: str

class FPLOptimizer:
    def __init__(self, bootstrap: dict, fixtures: list = None):
        self.bootstrap = bootstrap
        self.fixtures = fixtures or []
        self.elements_by_id = {e["id"]: e for e in bootstrap.get("elements", [])}
        self.teams_by_id = {t["id"]: t for t in bootstrap.get("teams", [])}
        self.types_by_id = {t["id"]: t for t in bootstrap.get("element_types", [])}

    def evaluate_player(self, element_id: int, selling_price: int = None, purchase_price: int = None) -> PlayerValuation:
        """Calculates expected points / value for a player considering form, ep_next, flags, and fixtures."""
        el = self.elements_by_id[element_id]
        team = self.teams_by_id[el["team"]]
        el_type = self.types_by_id[el["element_type"]]

        try:
            ep_next = float(el.get("ep_next") or 0.0)
        except (ValueError, TypeError):
            ep_next = 0.0

        try:
            form = float(el.get("form") or 0.0)
        except (ValueError, TypeError):
            form = 0.0

        try:
            ppg = float(el.get("points_per_game") or 0.0)
        except (ValueError, TypeError):
            ppg = 0.0

        if ep_next > 0:
            base_ev = ep_next * 0.7 + form * 0.2 + ppg * 0.1
        else:
            base_ev = form * 0.7 + ppg * 0.3

        status = el.get("status", "a")
        chance = el.get("chance_of_playing_next_round")
        
        is_flagged = False
        avail_multiplier = 1.0
        status_desc = "Available"

        if status != "a" or (chance is not None and chance < 100):
            is_flagged = True
            if chance is not None:
                if chance == 0:
                    avail_multiplier = 0.0
                    status_desc = f"Out (0% chance: {el.get('news', 'Injured / Transferred')})"
                elif chance == 25:
                    avail_multiplier = 0.20
                    status_desc = f"Doubtful (25% chance: {el.get('news', '')})"
                elif chance == 50:
                    avail_multiplier = 0.45
                    status_desc = f"Doubtful (50% chance: {el.get('news', '')})"
                elif chance == 75:
                    avail_multiplier = 0.80
                    status_desc = f"Likely (75% chance: {el.get('news', '')})"
            else:
                if status in ("i", "s", "u"):
                    avail_multiplier = 0.0
                    status_desc = f"Unavailable ({el.get('news', status)})"
                elif status == "d":
                    avail_multiplier = 0.50
                    status_desc = f"Doubtful ({el.get('news', '')})"

        ev = base_ev * avail_multiplier
        if avail_multiplier == 0.0:
            ev = -99.0

        s_price = selling_price if selling_price is not None else el["now_cost"]
        p_price = purchase_price if purchase_price is not None else el["now_cost"]

        return PlayerValuation(
            element=el,
            team=team,
            element_type=el_type,
            selling_price=s_price,
            purchase_price=p_price,
            expected_value=ev,
            is_injured_or_flagged=is_flagged,
            status_summary=status_desc
        )

    def optimize_lineup(self, squad_valuations: list[PlayerValuation]) -> tuple[list[dict], tuple, PlayerValuation, PlayerValuation]:
        """Solves the best Starting XI formation, ranks the bench, and selects Captain & Vice-Captain."""
        gkps = [p for p in squad_valuations if p.element_type["id"] == 1]
        defs = [p for p in squad_valuations if p.element_type["id"] == 2]
        mids = [p for p in squad_valuations if p.element_type["id"] == 3]
        fwds = [p for p in squad_valuations if p.element_type["id"] == 4]

        gkps.sort(key=lambda x: x.expected_value, reverse=True)
        defs.sort(key=lambda x: x.expected_value, reverse=True)
        mids.sort(key=lambda x: x.expected_value, reverse=True)
        fwds.sort(key=lambda x: x.expected_value, reverse=True)

        starting_gkp = gkps[0]
        bench_gkp = gkps[1] if len(gkps) > 1 else None

        best_formation = None
        best_score = -9999.0
        best_starters = []
        best_bench = []

        for (n_def, n_mid, n_fwd) in VALID_FORMATIONS:
            if len(defs) < n_def or len(mids) < n_mid or len(fwds) < n_fwd:
                continue

            chosen_defs = defs[:n_def]
            bench_defs = defs[n_def:]

            chosen_mids = mids[:n_mid]
            bench_mids = mids[n_mid:]

            chosen_fwds = fwds[:n_fwd]
            bench_fwds = fwds[n_fwd:]

            score = sum(p.expected_value for p in chosen_defs + chosen_mids + chosen_fwds)

            if score > best_score:
                best_score = score
                best_formation = (n_def, n_mid, n_fwd)
                best_starters = chosen_defs + chosen_mids + chosen_fwds
                outfield_bench = bench_defs + bench_mids + bench_fwds
                outfield_bench.sort(key=lambda x: x.expected_value, reverse=True)
                best_bench = outfield_bench

        all_starters = [starting_gkp] + best_starters
        sorted_starters = sorted(all_starters, key=lambda x: x.expected_value, reverse=True)
        captain = sorted_starters[0]
        
        vc_candidates = [p for p in sorted_starters[1:] if p.element["team"] != captain.element["team"]]
        vice_captain = vc_candidates[0] if vc_candidates else sorted_starters[1]

        final_picks = []
        pos_idx = 1
        for p in all_starters:
            final_picks.append({
                "element": p.element["id"],
                "position": pos_idx,
                "is_captain": (p.element["id"] == captain.element["id"]),
                "is_vice_captain": (p.element["id"] == vice_captain.element["id"]),
                "valuation": p
            })
            pos_idx += 1

        if bench_gkp:
            final_picks.append({
                "element": bench_gkp.element["id"],
                "position": 12,
                "is_captain": False,
                "is_vice_captain": False,
                "valuation": bench_gkp
            })

        for i, p in enumerate(best_bench):
            final_picks.append({
                "element": p.element["id"],
                "position": 13 + i,
                "is_captain": False,
                "is_vice_captain": False,
                "valuation": p
            })

        return final_picks, best_formation, captain, vice_captain

    def optimize_transfers(
        self,
        squad_valuations: list[PlayerValuation],
        bank: int,
        free_transfers: int,
        min_improvement: float = 0.75
    ) -> list[dict]:
        """
        Finds up to free_transfers optimal player upgrades.
        Prioritizes replacing non-playing outfielders (e.g. Watkins/Caicedo) before bench goalkeepers.
        """
        if free_transfers <= 0:
            return []

        current_squad = list(squad_valuations)
        current_bank = bank
        executed_transfers = []

        for _ in range(free_transfers):
            team_counts = {}
            for p in current_squad:
                tid = p.element["team"]
                team_counts[tid] = team_counts.get(tid, 0) + 1

            current_squad_ids = {p.element["id"] for p in current_squad}

            # Prioritize: 1) Outfielders who left or are out (EV < 0), 2) Flagged outfielders, 3) Active outfielders, 4) GKPs
            red_flags_outfield = [p for p in current_squad if p.expected_value < 0.0 and p.element_type["id"] != 1]
            flagged_outfielders = [p for p in current_squad if p.is_injured_or_flagged and p not in red_flags_outfield and p.element_type["id"] != 1]
            other_outfielders = [p for p in current_squad if p.element_type["id"] != 1 and p not in red_flags_outfield and p not in flagged_outfielders]
            other_outfielders.sort(key=lambda x: x.expected_value)
            gkps = [p for p in current_squad if p.element_type["id"] == 1]
            gkps.sort(key=lambda x: x.expected_value)

            sell_candidates = red_flags_outfield + flagged_outfielders + other_outfielders + gkps
            best_transfer = None
            best_gain = 0.0

            for player_out in sell_candidates:
                max_budget = player_out.selling_price + current_bank
                pos_type = player_out.element["element_type"]
                out_tid = player_out.element["team"]
                is_gkp = (pos_type == 1)

                for el in self.bootstrap.get("elements", []):
                    if el["id"] in current_squad_ids:
                        continue
                    if el["element_type"] != pos_type:
                        continue
                    if el["now_cost"] > max_budget:
                        continue
                    if el.get("status") not in ("a", "d"):
                        continue

                    in_tid = el["team"]
                    current_club_count = team_counts.get(in_tid, 0)
                    new_club_count = current_club_count if in_tid == out_tid else current_club_count + 1

                    if new_club_count > 3:
                        continue

                    val_in = self.evaluate_player(el["id"], selling_price=el["now_cost"], purchase_price=el["now_cost"])
                    
                    # Calculate gain
                    if player_out.expected_value < 0:
                        gain = val_in.expected_value
                    else:
                        gain = val_in.expected_value - max(player_out.expected_value, 0.0)

                    # If this is a bench backup goalkeeper upgrade, weight it lower than outfield starters
                    if is_gkp and player_out.expected_value >= 0.0:
                        gain *= 0.15

                    if gain > best_gain and gain >= min_improvement:
                        best_gain = gain
                        best_transfer = {
                            "player_out": player_out,
                            "player_in": val_in,
                            "gain": gain,
                            "selling_price": player_out.selling_price,
                            "purchase_price": val_in.element["now_cost"],
                            "cost": 0
                        }

            if best_transfer:
                executed_transfers.append(best_transfer)
                out_p = best_transfer["player_out"]
                in_p = best_transfer["player_in"]
                current_bank = current_bank + out_p.selling_price - in_p.element["now_cost"]
                current_squad = [p for p in current_squad if p.element["id"] != out_p.element["id"]] + [in_p]
            else:
                break

        return executed_transfers
