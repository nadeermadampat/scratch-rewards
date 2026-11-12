import type { Activity, CardStatus } from "../../api/types";
import { formatDateTime } from "../../lib/util";

// Icon + label, so status never depends on colour alone.
const STATUS: Record<CardStatus, string> = {
  issued: "○ Issued",
  opened: "◔ Opened",
  scratching: "◑ Scratching",
  completed: "● Scratched",
  expired: "✕ Expired",
};

const REDEMPTION: Record<string, string> = {
  not_applicable: "—",
  pending: "Pending",
  redeemed: "✓ Redeemed",
};

export function ActivityTable({ rows }: { rows: Activity[] }) {
  return (
    <section className="panel mt-6 p-5">
      <h2 className="font-display text-lg font-bold">Recent activity</h2>
      <p className="mt-0.5 text-xs text-white/50">Latest {rows.length} scratch cards. Results stay hidden until a card is scratched.</p>
      {rows.length === 0 ? (
        <p className="mt-6 text-center text-sm text-white/50">No scratch cards yet. Share the landing page to get started.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead>
              <tr className="text-left text-xs text-white/50">
                <th className="pb-2 pr-3 font-medium">Generated</th>
                <th className="pb-2 pr-3 font-medium">Participant</th>
                <th className="pb-2 pr-3 font-medium">Card</th>
                <th className="pb-2 pr-3 font-medium">Status</th>
                <th className="pb-2 pr-3 font-medium">Result</th>
                <th className="pb-2 pr-3 font-medium">Claim reference</th>
                <th className="pb-2 pr-3 font-medium">Redemption</th>
                <th className="pb-2 pr-3 text-right font-medium" title="Times the participant came back through the campaign and got this card again">Return visits</th>
                <th className="pb-2 text-right font-medium" title="Times the finished card was scratched again">Replays</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.card_reference} className="border-t border-white/[0.07]">
                  <td className="whitespace-nowrap py-2.5 pr-3 tabular-nums text-white/70">{formatDateTime(row.generated_at)}</td>
                  <td className="py-2.5 pr-3">{row.user_label}</td>
                  <td className="py-2.5 pr-3 font-mono text-xs text-white/55">#{row.card_reference}</td>
                  <td className="whitespace-nowrap py-2.5 pr-3">{STATUS[row.status] ?? row.status}</td>
                  <td className="py-2.5 pr-3">{row.reward_name ?? <span className="text-white/35">Hidden</span>}</td>
                  <td className="py-2.5 pr-3 font-mono text-xs">{row.claim_reference ?? "—"}</td>
                  <td className="whitespace-nowrap py-2.5 pr-3">{REDEMPTION[row.redemption_status] ?? row.redemption_status}</td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">{row.return_visits || "—"}</td>
                  <td className="py-2.5 text-right tabular-nums">{row.replays || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
