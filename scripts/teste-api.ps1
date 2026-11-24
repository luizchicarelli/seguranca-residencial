# Testa a API e mostra os dados gravados (serve também para o vídeo e para o teste "painel fechado").
# Uso:
#   $env:API_URL = "https://SEU-PROJETO.supabase.co/functions/v1/readings"
#   $env:DEVICE_KEY = "sua-device-key"      # só necessário sem -SomenteConsulta
#   ./scripts/teste-api.ps1                  # envia um lote de teste + consulta
#   ./scripts/teste-api.ps1 -SomenteConsulta # só consulta (não grava nada)
#   ./scripts/teste-api.ps1 -SomenteConsulta -Alarme on   # arma (ou "off" para desarmar)
param([switch]$SomenteConsulta, [ValidateSet("on", "off")][string]$Alarme)
$ErrorActionPreference = "Stop"
$api = $env:API_URL
if (-not $api) { throw "Defina `$env:API_URL antes de rodar." }

if (-not $SomenteConsulta) {
  # Lote em um único POST, como o ESP32 faz. Usa um device_id de teste para não bagunçar a planta.
  $lote = ConvertTo-Json -Compress @(
    @{ device_id = "teste-script"; metric = "magnetic_field"; value = 50.0; unit = "mT"; state = "closed"; alert = $false },
    @{ device_id = "teste-script"; metric = "presence"; value = 0; unit = "bool"; state = "clear"; alert = $false }
  )

  "--- POST de um lote com a chave correta (esperado: 201) ---"
  Invoke-RestMethod -Method Post -Uri $api -Headers @{ "x-device-key" = $env:DEVICE_KEY } -ContentType "application/json" -Body $lote

  "--- POST com a chave errada (esperado: 401) ---"
  try {
    Invoke-RestMethod -Method Post -Uri $api -Headers @{ "x-device-key" = "errada" } -ContentType "application/json" -Body $lote | Out-Null
    throw "FALHOU: a API aceitou uma chave errada"
  } catch [System.Net.WebException] {
    "OK: rejeitada com status $([int]$_.Exception.Response.StatusCode)"
  }
}

if ($Alarme) {
  "--- Alarme: $Alarme ---"
  Invoke-RestMethod -Method Post -Uri "$api/alarm" -ContentType "application/json" -Body (@{ armed = ($Alarme -eq "on") } | ConvertTo-Json)
}

"--- Estado da casa (GET /status) ---"
$status = Invoke-RestMethod "$api/status"
"Alarme armado: $($status.armed)"
$status.sensors | Format-Table device_id, value, unit, state, alert, created_at

"--- Histórico da porta de entrada (últimas 10) ---"
Invoke-RestMethod "${api}?device_id=porta-entrada&limit=10" | Format-Table created_at, value, unit, state, alert
