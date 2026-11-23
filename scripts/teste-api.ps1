# Testa a API e mostra os dados gravados (serve também para o vídeo e para o teste "painel fechado").
# Uso:
#   $env:API_URL = "https://SEU-PROJETO.supabase.co/functions/v1/readings"
#   $env:DEVICE_KEY = "sua-device-key"      # só necessário sem -SomenteConsulta
#   ./scripts/teste-api.ps1                  # envia 1 leitura de teste + consulta
#   ./scripts/teste-api.ps1 -SomenteConsulta # só consulta (não grava nada)
param([switch]$SomenteConsulta)
$ErrorActionPreference = "Stop"
$api = $env:API_URL
$dev = "porta-01"
if (-not $api) { throw "Defina `$env:API_URL antes de rodar." }

if (-not $SomenteConsulta) {
  $body = @{ device_id = $dev; metric = "magnetic_field"; value = 50.0; unit = "mT"; state = "closed"; alert = $false } | ConvertTo-Json

  "--- POST com a chave correta (esperado: 201) ---"
  Invoke-RestMethod -Method Post -Uri $api -Headers @{ "x-device-key" = $env:DEVICE_KEY } -ContentType "application/json" -Body $body

  "--- POST com a chave errada (esperado: 401) ---"
  try {
    Invoke-RestMethod -Method Post -Uri $api -Headers @{ "x-device-key" = "errada" } -ContentType "application/json" -Body $body | Out-Null
    throw "FALHOU: a API aceitou uma chave errada"
  } catch [System.Net.WebException] {
    "OK: rejeitada com status $([int]$_.Exception.Response.StatusCode)"
  }
}

"--- Leitura mais recente (GET /latest) ---"
Invoke-RestMethod "$api/latest?device_id=$dev" | Format-List created_at, device_id, metric, value, unit, state, alert

"--- Histórico (GET, últimas 10) ---"
Invoke-RestMethod "${api}?device_id=$dev&limit=10" | Format-Table created_at, value, unit, state, alert
