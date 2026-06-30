# x_fetch.ps1 — pull recent X posts for the fantasy dossier (runs on YOUR machine, where the network is open).
# Reads the Bearer token from X_BEARER_TOKEN.txt in the same folder. Writes x_posts.json next to it.
# No installs needed — pure PowerShell. Handles-only pull: 48 analyst handles x 20 recent posts (~$5, 7-day window).

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- token (from the X_BEARER_TOKEN.txt you already have in this folder) ---
$tokenFile = Join-Path $dir "X_BEARER_TOKEN.txt"
if (-not (Test-Path $tokenFile)) { Write-Host "ERROR: X_BEARER_TOKEN.txt not found in $dir" -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
$raw = (Get-Content -Raw $tokenFile).Trim()
if ($raw -match '(?i)^X_BEARER_TOKEN\s*[=:]\s*(.+)$') { $token = $Matches[1].Trim() } else { $token = $raw }
$token = $token.Trim('"').Trim("'").Trim()
if ($token.Length -lt 40) { Write-Host "ERROR: token in X_BEARER_TOKEN.txt looks too short ($($token.Length) chars)." -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
Write-Host "Token loaded ($($token.Length) chars)."

$handles = @('32beatwriters','4for4_john','4for4football','adamlevitan','ahaanrungta','aschatznfl','benjaminsolak','brettkollmann','chessliam','clevta','coachspeakindex','connorallennfl','dbro_ffb','dhananizain','fantasypts','fantasyptsdata','fball_insights','ffdataroma','ffnatejahnke','grahambarfield','haydenwinks','ihartitz','jagibbs_23','jakobsanderson','jamesdkoh','johntoddnfl','joshnorris','koalatystats','lateroundqb','mattharmon_byb','mikeclaynfl','nextgenstats','ooooftw','pat_thorman','patkerrane','pff_fantasy','rotostreetwolf','ryanj_heath','ryanmc23','sammonsonnfl','scottbarrettdfb','sigmundbloom','smitchell17','sumersports','superrnova38','syedschemes','tejfbanalytics','the_oddsmaker')
$perHandle = 20
$base = "https://api.x.com/2/tweets/search/recent"
$headers = @{ Authorization = "Bearer $token" }

Write-Host ("Pulling recent posts from {0} handles x {1} (~`${2}, 7-day window)..." -f $handles.Count, $perHandle, [math]::Round($handles.Count*$perHandle*0.005,2))

function Get-Search($query) {
  $q = [uri]::EscapeDataString($query)
  $url = "$base" + "?query=$q&max_results=$perHandle&tweet.fields=created_at,public_metrics&expansions=author_id&user.fields=username,name"
  for ($try = 0; $try -lt 3; $try++) {
    try { return Invoke-RestMethod -Uri $url -Headers $headers -Method Get }
    catch {
      $code = 0; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
      if ($code -eq 429) { Write-Host "  rate-limited; waiting 60s..." -ForegroundColor Yellow; Start-Sleep -Seconds 60; continue }
      if ($code -eq 401 -or $code -eq 403) { Write-Host "AUTH ERROR $code — the token was rejected. Regenerate the Bearer token in the X console and re-save X_BEARER_TOKEN.txt." -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
      Write-Host "  HTTP $code; skipping" -ForegroundColor Yellow; return $null
    }
  }
  return $null
}

$posts = New-Object System.Collections.ArrayList
$i = 0
foreach ($h in $handles) {
  $i++
  $r = Get-Search("from:$h -is:retweet")
  if ($r -and $r.data) {
    $users = @{}; if ($r.includes -and $r.includes.users) { foreach ($u in $r.includes.users) { $users[$u.id] = $u } }
    foreach ($t in $r.data) {
      $u = $users[$t.author_id]
      [void]$posts.Add([pscustomobject]@{
        handle = $(if ($u) { $u.username } else { $h }); name = $(if ($u) { $u.name } else { $null })
        text = $t.text; date = $t.created_at; likes = $t.public_metrics.like_count
        url = "https://x.com/i/status/$($t.id)"; kind = "tweet"; source = "x_api" })
    }
  }
  Write-Host ("  [{0}/{1}] @{2} -> {3} posts so far" -f $i, $handles.Count, $h, $posts.Count)
  Start-Sleep -Milliseconds 400
}

$out = Join-Path $dir "x_posts.json"
$posts | ConvertTo-Json -Depth 6 | Out-File -FilePath $out -Encoding utf8
Write-Host ""
Write-Host ("DONE — {0} posts written to {1}" -f $posts.Count, $out) -ForegroundColor Green
Write-Host "Upload x_posts.json back to the chat and I'll map it into the dossier."
Read-Host "Enter to close"
