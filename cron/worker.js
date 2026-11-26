/**
 * Cron tetikleyici — GitHub Actions "Veri yenile ve yayinla" isini baslatir.
 *
 * NEDEN VAR (26.11.2026 olcumu):
 *   GitHub'in kendi schedule'i 2 saatlik cron'u ~10 saatte bire dusuruyordu
 *   (olculen araliklar 5.7 - 13.1 saat). Gunluk veri tazeleme bu yuzden aksiyordu.
 *   Dis tetikleyici (cron-job.org) ise 422 verdigi icin hic calismiyordu.
 *
 *   Cloudflare Workers cron trigger'lari zamaninda calisir ve ucretsiz planda
 *   gunde 5 tetiklemeye kadar izin verilir. Bu Worker yalnizca GitHub API'sine
 *   workflow_dispatch cagrisi yapar; veri isleme GitHub'da kalir.
 *
 * GEREKLI SIR (wrangler secret put):
 *   GH_PAT  — fine-grained PAT, "Actions: read and write" izni
 */
export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env, "cron"));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Elle tetikleme: /?token=<CRON_SECRET>  (test ve acil durum icin)
    if (url.pathname === "/" && request.method === "POST") {
      const given = url.searchParams.get("token") || request.headers.get("x-cron-token") || "";
      if (!env.CRON_SECRET || given !== env.CRON_SECRET) {
        return json({ ok: false, error: "Yetkisiz." }, 401);
      }
      const r = await dispatch(env, "manual");
      return json(r, r.ok ? 200 : 502);
    }

    if (url.pathname === "/" || url.pathname === "/health") {
      return json({
        ok: true,
        service: "tokenmaliyet-cron",
        workflow: env.GH_WORKFLOW || "refresh.yml",
        repo: env.GH_REPO || "S7lverl7ght/tokenmaliyet",
        hasPat: Boolean(env.GH_PAT),
      });
    }
    return json({ ok: false, error: "Bulunamadi." }, 404);
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

async function dispatch(env, reason) {
  if (!env.GH_PAT) {
    return { ok: false, reason, error: "GH_PAT tanimli degil." };
  }
  const repo = env.GH_REPO || "S7lverl7ght/tokenmaliyet";
  const wf = env.GH_WORKFLOW || "refresh.yml";
  const url = `https://api.github.com/repos/${repo}/actions/workflows/${wf}/dispatches`;

  try {
    const r = await fetch(url, {
      method: "POST",
      headers: {
        authorization: "Bearer " + env.GH_PAT,
        accept: "application/vnd.github+json",
        "user-agent": "tokenmaliyet-cron",
        "content-type": "application/json",
        "x-github-api-version": "2022-11-28",
      },
      // GitHub bu ucu 422 ile reddeder eger govde yanlissa:
      //   govde yok -> 422, {} -> 422 ("ref" wasn't supplied), {"ref":"master"} -> 422
      body: JSON.stringify({ ref: env.GH_REF || "main" }),
    });

    if (r.status === 204) {
      return { ok: true, reason, dispatched: true, status: 204 };
    }
    const detail = await r.text();
    return { ok: false, reason, status: r.status, error: detail.slice(0, 300) };
  } catch (e) {
    return { ok: false, reason, error: String(e).slice(0, 200) };
  }
}
