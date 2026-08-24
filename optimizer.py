"""
FPL Optimization Engine: Player valuation, Formation solver, Captaincy selector, and Transfer optimizer.
"""
from dataclasses import dataclass
from typing import Optional

# Valid FPL outfield formations: (DEF, MID, FWD) where DEF >= 3, MID >= 2, FWD >= 1 and sum == 10
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
        """
        Calculates expected points / value for a player considering form, ep_next,
        injury flags, and fixture difficulty.
        """
        el = self.elements_by_id[element_id]
        team = self.teams_by_id[el["team"]]
        el_type = self.types_by_id[el["element_type"]]

        # Base Expected Points (using FPL's ep_next, with form & points_per_game fallback)
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

        # Availability / Injury Multiplier
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
                    status_desc = f"Out (0% chance: {el.get('news', 'Injured')})"
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
        # Ensure red-flagged players get strong negative penalty so they are never in starting 11
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
        """
        Solves the best Starting XI formation, ranks the bench in priority order,
        and selects Captain (C) and Vice-Captain (VC).
        """
        # Separate by position
        gkps = [p for p in squad_valuations if p.element_type["id"] == 1]
        defs = [p for p in squad_valuations if p.element_type["id"] == 2]
        mids = [p for p in squad_valuations if p.element_type["id"] == 3]
        fwds = [p for p in squad_valuations if p.element_type["id"] == 4]

        # Sort each group by expected value descending
        gkps.sort(key=lambda x: x.expected_value, reverse=True)
        defs.sort(key=lambda x: x.expected_value, reverse=True)
        mids.sort(key=lambda x: x.expected_value, reverse=True)
        fwds.sort(key=lambda x: x.expected_value, reverse=True)

        # 1 Starting Goalkeeper, 1 Bench Goalkeeper
        starting_gkp = gkps[0]
        bench_gkp = gkps[1] if len(gkps) > 1 else None

        # Solve for best outfield formation
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
                
                # Outfield bench candidates
                outfield_bench = bench_defs + bench_mids + bench_fwds
                # Sort outfield bench by expected points descending (so best backup subs first)
                outfield_bench.sort(key=lambda x: x.expected_value, reverse=True)
                best_bench = outfield_bench

        all_starters = [starting_gkp] + best_starters
        # Captain is highest EV starter, Vice-Captain is 2nd highest
        sorted_starters = sorted(all_starters, key=lambda x: x.expected_value, reverse=True)
        captain = sorted_starters[0]
        
        # Pick vice captain (prefer different team if possible)
        vc_candidates = [p for p in sorted_starters[1:] if p.element["team"] != captain.element["team"]]
        vice_captain = vc_candidates[0] if vc_candidates else sorted_starters[1]

        # Build final 15-player picks list for FPL API
        # Positions 1-11: Starting XI (1 GKP, then DEFs, MIDs, FWDs)
        # Position 12: Bench GKP
        # Positions 13, 14, 15: Outfield Bench in priority order
        final_picks = []
        
        # Starters
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

        # Bench GKP (Position 12)
        if bench_gkp:
            final_picks.append({
                "element": bench_gkp.element["id"],
                "position": 12,
                "is_captain": False,
                "is_vice_captain": False,
                "valuation": bench_gkp
            })

        # Outfield Bench (Positions 13, 14, 15)
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
    ) -> Optional[dict]:
        """
        Finds the single best free transfer upgrade if beneficial.
        Respects budget (player sell price + bank) and club limits (max 3 per club).
        """
        if free_transfers <= 0:
            return None

        # Count players per team currently
        team_counts = {}
        for p in squad_valuations:
            tid = p.element["team"]
            team_counts[tid] = team_counts.get(tid, 0) + 1

        current_squad_ids = {p.element["id"] for p in squad_valuations}

        # Identify sell candidates (flagged/injured players first, then lowest EV outfielders)
        flagged_players = [p for p in squad_valuations if p.is_injured_or_flagged or p.expected_value <= 0.0]
        other_players = [p for p in squad_valuations if p not in flagged_players]
        other_players.sort(key=lambda x: x.expected_value)

        # Candidate order: red flags first, then weakest players
        sell_candidates = flagged_players + other_players

        best_transfer = None
        best_gain = 0.0

        for player_out in sell_candidates:
            max_budget = player_out.selling_price + bank
            pos_type = player_out.element["element_type"]
            out_tid = player_out.element["team"]

            # Filter market for players in same position within budget
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
                # Check club constraint (max 3 per club)
                current_club_count = team_counts.get(in_tid, 0)
                if in_tid == out_tid:
                    new_club_count = current_club_count # swapping within same club
                else:
                    new_club_count = current_club_count + 1

                if new_club_count > 3:
                    continue

                # Evaluate potential target
                val_in = self.evaluate_player(el["id"], selling_price=el["now_cost"], purchase_price=el["now_cost"])
                gain = val_in.expected_value - max(player_out.expected_value, 0.0)

                # If selling a red-flagged player with 0 EV, any healthy positive EV is a huge gain
                if player_out.expected_value < 0:
                    gain = val_in.expected_value

                if gain > best_gain and gain >= min_improvement:
                    best_gain = gain
                    best_transfer = {
                        "player_out": player_out,
                        "player_in": val_in,
                        "gain": gain,
                        "selling_price": player_out.selling_price,
                        "purchase_price": val_in.element["now_cost"],
                        "cost": 0 # 1 FT = 0 hit points
                    }

        return best_transfer
