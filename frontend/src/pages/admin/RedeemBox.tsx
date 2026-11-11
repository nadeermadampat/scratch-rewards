import { useState } from "react";
import type { FormEvent } from "react";
import type { AdminApi } from "../../api/client";
import { ApiError } from "../../api/client";
import { Spinner } from "../../components/ui";

/** Counter staff enter a customer's claim reference to mark the prize as handed over. */
export function RedeemBox({ client, onRedeemed }: { client: AdminApi; onRedeemed: () => Promise<void> | void }) {
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const result = await client.redeem(reference.trim());
      setMessage({ ok: true, text: `✓ ${result.reward_name} marked as redeemed.` });
      setReference("");
      await onRedeemed();
    } catch (e) {
      setMessage({ ok: false, text: (e as ApiError).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel h-fit p-5">
      <h2 className="font-display text-lg font-bold">Redeem a reward</h2>
      <p className="mt-0.5 text-xs text-white/50">Enter the claim reference shown on the customer's result page.</p>
      <form onSubmit={submit} className="mt-4 space-y-3">
        <input
          className="field font-mono uppercase tracking-wider"
          placeholder="SCR-XXXXX-XXXXX"
          aria-label="Claim reference"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          maxLength={24}
        />
        <button className="btn-primary w-full" disabled={busy || reference.trim().length < 6}>
          {busy ? <Spinner /> : "Mark as redeemed"}
        </button>
      </form>
      {message && (
        <p role="status" className={`mt-3 text-sm ${message.ok ? "text-emerald-300" : "text-red-300"}`}>
          {message.text}
        </p>
      )}
    </section>
  );
}
