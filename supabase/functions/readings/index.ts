// API REST — Supabase Edge Function "readings"
//   POST /readings                          (ESP32 envia leitura; exige header x-device-key)
//   GET  /readings/latest?device_id=...     (leitura mais recente)
//   GET  /readings?device_id=...&limit=50   (histórico, mais recente primeiro)
// Deploy com verificação de JWT DESLIGADA: a autenticação do POST é a DEVICE_KEY.
import { createClient } from "npm:@supabase/supabase-js@2";

const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);
const DEVICE_KEY = Deno.env.get("DEVICE_KEY"); // secret configurado no painel da Supabase

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-device-key, authorization, apikey",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });

const isStr = (v: unknown, max: number) =>
  typeof v === "string" && v.length > 0 && v.length <= max;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });

  const url = new URL(req.url);
  const route = url.pathname.replace(/^.*\/readings/, ""); // "" ou "/latest"

  if (req.method === "POST" && route === "") {
    if (!DEVICE_KEY || req.headers.get("x-device-key") !== DEVICE_KEY) {
      return json({ error: "dispositivo não autorizado" }, 401);
    }
    let b: Record<string, unknown>;
    try {
      b = await req.json();
    } catch {
      return json({ error: "JSON inválido" }, 400);
    }
    const valid =
      isStr(b.device_id, 64) && isStr(b.metric, 32) && isStr(b.unit, 16) &&
      typeof b.value === "number" && Number.isFinite(b.value) &&
      (b.state === undefined || b.state === "open" || b.state === "closed") &&
      (b.alert === undefined || typeof b.alert === "boolean");
    if (!valid) return json({ error: "campos inválidos" }, 400);

    const { data, error } = await db.from("readings").insert({
      device_id: b.device_id,
      metric: b.metric,
      value: b.value,
      unit: b.unit,
      state: b.state ?? null,
      alert: b.alert ?? false,
    }).select().single();
    if (error) return json({ error: error.message }, 500);

    console.log("leitura recebida", JSON.stringify(data)); // aparece em Edge Functions > Logs
    return json(data, 201);
  }

  if (req.method === "GET" && (route === "" || route === "/latest")) {
    const device = url.searchParams.get("device_id");
    if (!device) return json({ error: "device_id é obrigatório" }, 400);
    const limit = route === "/latest"
      ? 1
      : Math.min(Math.max(Number(url.searchParams.get("limit")) || 50, 1), 500);

    const { data, error } = await db.from("readings").select("*")
      .eq("device_id", device)
      .order("created_at", { ascending: false })
      .limit(limit);
    if (error) return json({ error: error.message }, 500);

    if (route === "/latest") {
      return data.length ? json(data[0]) : json({ error: "sem leituras" }, 404);
    }
    return json(data);
  }

  return json({ error: "rota não encontrada" }, 404);
});
