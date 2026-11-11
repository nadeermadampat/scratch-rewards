import { useState } from "react";
import type { AdminApi } from "../../api/client";
import { ApiError } from "../../api/client";
import type { RewardDistribution } from "../../api/types";

interface Props {
  rows: RewardDistribution[];
  client: AdminApi;
  onChanged: () => Promise<void> | void;
}

const pct = (share: number) => `${(share * 100).toFixed(share > 0 && share < 0.1 ? 1 : 0)}%`;

/** Reward odds (editable) next to how cards were actually distributed. */
export function RewardTable({ rows, client, onChanged }: Props) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const totalAssigned = rows.reduce((sum, row) => sum + row.assigned, 0);
  // One shared scale for bars and ticks so rows are comparable.
  const scaleMax = Math.max(0.01, ...rows.map((r) => Math.max(r.configured_share, totalAssigned ? r.assigned / totalAssigned : 0)));

  const save = async (row: RewardDistribution, changes: { weight?: number; is_active?: boolean }) => {
    setSavingId(row.reward_id);
    setError(null);
    try {
      await client.updateReward(row.reward_id, changes);
      setDrafts(({ [row.reward_id]: _saved, ...rest }) => rest);
      await onChanged();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <section className="panel min-w-0 p-5">
      <h2 className="font-display text-lg font-bold">Rewards: odds and distribution</h2>
      <p className="mt-0.5 text-xs text-white/50">
        Changing a weight affects cards issued from now on. Rewards already assigned to cards never change.
      </p>
      {error && <p role="alert" className="mt-3 text-sm text-red-300">{error}</p>}

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="text-left text-xs font-medium text-white/50">
              <th className="pb-2 pr-3 font-medium">Reward</th>
              <th className="pb-2 pr-3 font-medium">Weight</th>
              <th className="pb-2 pr-3 font-medium">Odds</th>
              <th className="w-[26%] pb-2 pr-3 font-medium">Share of issued cards</th>
              <th className="pb-2 pr-3 text-right font-medium">Issued</th>
              <th className="pb-2 pr-3 text-right font-medium">Revealed</th>
              <th className="pb-2 font-medium">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const actual = totalAssigned ? row.assigned / totalAssigned : 0;
              const draft = drafts[row.reward_id];
              const parsed = Number(draft);
              const dirty = draft !== undefined && draft !== String(row.weight);
              const valid = draft !== undefined && draft.trim() !== "" && Number.isFinite(parsed) && parsed >= 0;
              return (
                <tr key={row.reward_id} className={`border-t border-white/[0.07] ${row.is_active ? "" : "text-white/40"}`}>
                  <td className="py-2.5 pr-3">
                    <span className="mr-2">{row.icon}</span>
                    {row.name}
                    {!row.is_prize && <span className="ml-2 text-xs text-white/40">no prize</span>}
                    {row.total_quantity !== null && (
                      <span className="ml-2 text-xs text-white/40">stock {row.assigned}/{row.total_quantity}</span>
                    )}
                  </td>
                  <td className="py-2.5 pr-3">
                    <div className="flex items-center gap-1.5">
                      <input
                        className="field w-20 px-2 py-1.5 text-sm tabular-nums"
                        type="number"
                        min={0}
                        step="any"
                        aria-label={`Weight for ${row.name}`}
                        value={draft ?? String(row.weight)}
                        onChange={(e) => setDrafts((d) => ({ ...d, [row.reward_id]: e.target.value }))}
                      />
                      {dirty && (
                        <button
                          className="rounded-lg bg-accent px-2.5 py-1.5 text-xs font-semibold text-ink disabled:opacity-40"
                          disabled={!valid || savingId === row.reward_id}
                          onClick={() => void save(row, { weight: parsed })}
                        >
                          Save
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 pr-3 tabular-nums">{pct(row.configured_share)}</td>
                  <td className="py-2.5 pr-3">
                    <div
                      className="group relative flex items-center gap-2"
                      title={`${row.name}: ${pct(actual)} of issued cards (${row.assigned}) · configured odds ${pct(row.configured_share)}`}
                    >
                      <div className="relative h-3 flex-1 rounded-sm bg-white/[0.06]">
                        <div className="h-full rounded-r-[4px] bg-violet-400 group-hover:bg-violet-300" style={{ width: `${(actual / scaleMax) * 100}%` }} />
                        <div
                          className="absolute -bottom-1 -top-1 w-0.5 rounded bg-white/85"
                          style={{ left: `calc(${(row.configured_share / scaleMax) * 100}% - 1px)` }}
                        />
                      </div>
                      <span className="w-11 text-right tabular-nums text-white/75">{pct(actual)}</span>
                    </div>
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">{row.assigned}</td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">{row.revealed}</td>
                  <td className="py-2.5">
                    <input
                      type="checkbox"
                      className="h-5 w-5 accent-[rgb(var(--accent))]"
                      aria-label={`${row.name} active`}
                      checked={row.is_active}
                      disabled={savingId === row.reward_id}
                      onChange={(e) => void save(row, { is_active: e.target.checked })}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-white/50">
        <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-5 rounded-r-[3px] bg-violet-400" /> actual share of issued cards</span>
        <span className="flex items-center gap-1.5"><span className="inline-block h-3.5 w-0.5 rounded bg-white/85" /> configured odds</span>
      </p>
    </section>
  );
}
