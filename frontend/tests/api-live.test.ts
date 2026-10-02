import { strict as assert } from "node:assert";
import { test } from "node:test";
import type { AdviceRequest } from "../lib/types";
process.env.NEXT_PUBLIC_USE_MOCK = "false";
const request: AdviceRequest = {
  crop: "onion",
  quantity_qtl: 10,
  village: "Niphad",
  lot_condition: null,
  cash_needed_in_days: null,
  blocked_mandis: [],
  overrides: null,
  lang: "en",
};
test("live API preserves validation errors and visibly falls back only on unavailable responses", async () => {
  const { ApiError, getAdvice } = await import("../lib/api");
  const original = globalThis.fetch;
  try {
    const { demoAdvice } = await import("../lib/demo");
    const responseAdvice = demoAdvice(request);
    globalThis.fetch = async (url, init) => {
      assert.match(String(url), /\/advise$/);
      assert.equal(init?.method, "POST");
      assert.deepEqual(JSON.parse(String(init?.body)), request);
      return new Response(JSON.stringify(responseAdvice), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };
    const live = await getAdvice(request);
    assert.equal(live.mock, false);
    assert.equal(live.data.mandi, responseAdvice.mandi);
    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({ error: "Village not covered", field: "village" }),
        { status: 400 },
      );
    await assert.rejects(
      getAdvice(request),
      (error) =>
        error instanceof ApiError &&
        error.field === "village" &&
        error.message === "Village not covered",
    );
    globalThis.fetch = async () => new Response("unavailable", { status: 503 });
    const fallback = await getAdvice(request);
    assert.equal(fallback.mock, true);
    assert.match(fallback.fallback!, /Backend unavailable/);
    globalThis.fetch = async () => {
      throw new TypeError("Failed to fetch");
    };
    assert.equal((await getAdvice(request)).mock, true);
    globalThis.fetch = async () => new Response("not json", { status: 200 });
    assert.equal((await getAdvice(request)).mock, true);
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ action: "hold" }), { status: 200 });
    assert.equal((await getAdvice(request)).mock, true);
  } finally {
    globalThis.fetch = original;
  }
});
