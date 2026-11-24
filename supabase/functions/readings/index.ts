// API REST — Supabase Edge Function "readings"
//   POST /readings                          ESP32 envia uma leitura ou um lote (array) de leituras.
//                                           Exige header x-device-key. Responde { inserted, armed }.
//   GET  /readings/latest?device_id=...     leitura mais recente de um sensor
//   GET  /readings?device_id=...&limit=50   histórico de um sensor (mais recente primeiro)
//   GET  /readings/status                   última leitura de cada sensor + estado do alarme
//   POST /readings/alarm   { "armed": true } arma/desarma o alarme (aberto, sem autenticação:
//                                           decisão de projeto para o trabalho acadêmico)
// Deploy com verificação de JWT DESLIGADA: a autenticação do POST de leituras é a DEVICE_KEY.
import { createClient } from "npm:@supabase/supabase-js@2";

const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);
const DEVICE_KEY = Deno.env.get("DEVICE_KEY"); // secret configurado no painel da Supabase
const MAX_BATCH = 20;
const STATES = ["open", "closed", "motion", "clear"];

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

// deno-lint-ignore no-explicit-any
const isValidReading = (b: any) =>
  b !== null && typeof b === "object" &&
  isStr(b.device_id, 64) && isStr(b.metric, 32) && isStr(b.unit, 16) &&
  typeof b.value === "number" && Number.isFinite(b.value) &&
  (b.state === undefined || STATES.includes(b.state)) &&
  (b.alert === undefined || typeof b.alert === "boolean");

async function isArmed() {
  const { data, error } = await db.from("alarm").select("armed").eq("id", 1).single();
  if (error) throw error;
  return data.armed as boolean;
}

async function readBody(req: Request) {
  try {
    return await req.json();
  } catch {
    return undefined;
  }
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });

  const url = new URL(req.url);
  const route = url.pathname.replace(/^.*\/readings/, ""); // "", "/latest", "/status" ou "/alarm"

  try {
    // ---- Dispositivo envia leituras (uma ou um lote) ----
    if (req.method === "POST" && route === "") {
      if (!DEVICE_KEY || req.headers.get("x-device-key") !== DEVICE_KEY) {
        return json({ error: "dispositivo não autorizado" }, 401);
      }
      const body = await readBody(req);
      const list = Array.isArray(body) ? body : [body];
      if (list.length === 0 || list.length > MAX_BATCH || !list.every(isValidReading)) {
        return json({ error: `envie 1 a ${MAX_BATCH} leituras com campos válidos` }, 400);
      }

      const rows = list.map((b) => ({
        device_id: b.device_id,
        metric: b.metric,
        value: b.value,
        unit: b.unit,
        state: b.state ?? null,
        alert: b.alert ?? false,
      }));
      const { error } = await db.from("readings").insert(rows);
      if (error) return json({ error: error.message }, 500);

      console.log(`${rows.length} leitura(s) recebida(s)`, JSON.stringify(rows)); // Edge Functions > Logs
      // A resposta leva o estado do alarme de volta ao ESP32 (comunicação nos dois sentidos).
      return json({ inserted: rows.length, armed: await isArmed() }, 201);
    }

    // ---- Painel arma/desarma o alarme ----
    if (req.method === "POST" && route === "/alarm") {
      const body = await readBody(req);
      if (typeof body?.armed !== "boolean") return json({ error: "envie { \"armed\": true|false }" }, 400);
      const { data, error } = await db.from("alarm")
        .update({ armed: body.armed, updated_at: new Date().toISOString() })
        .eq("id", 1).select().single();
      if (error) return json({ error: error.message }, 500);
      console.log("alarme", body.armed ? "ARMADO" : "DESARMADO");
      return json(data);
    }

    // ---- Painel: estado geral da casa ----
    if (req.method === "GET" && route === "/status") {
      const [sensors, alarm] = await Promise.all([
        db.from("latest_readings").select("*"),
        db.from("alarm").select("armed, updated_at").eq("id", 1).single(),
      ]);
      if (sensors.error) return json({ error: sensors.error.message }, 500);
      if (alarm.error) return json({ error: alarm.error.message }, 500);
      return json({ armed: alarm.data.armed, alarm_updated_at: alarm.data.updated_at, sensors: sensors.data });
    }

    // ---- Última leitura e histórico de um sensor ----
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
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
});
