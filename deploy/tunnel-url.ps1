<#
.SYNOPSIS
  Prints the current public HTTPS URL of the cloudflared quick tunnel.
.DESCRIPTION
  Reads the URL from the cloudflared pod logs. If the logs no longer hold it, asks
  cloudflared's own /quicktunnel endpoint through the Kubernetes API server.
  The URL changes whenever the cloudflared pod restarts.
.EXAMPLE
  deploy/tunnel-url.ps1
  deploy/tunnel-url.ps1 -Wait      # poll for up to two minutes after a fresh apply
#>
[CmdletBinding()]
param(
    [string]$Namespace = 'confpilot',
    [switch]$Wait
)

$ErrorActionPreference = 'Stop'
$selector = 'app.kubernetes.io/name=cloudflared'
$pattern = 'https://[a-z0-9-]+\.trycloudflare\.com'

function Get-TunnelUrl {
    $logs = kubectl -n $Namespace logs -l $selector --tail=-1 2>$null
    $found = $logs | Select-String -Pattern $pattern -AllMatches |
        ForEach-Object { $_.Matches.Value } | Select-Object -Last 1
    if ($found) { return $found }

    $pod = kubectl -n $Namespace get pods -l $selector `
        --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>$null
    if (-not $pod) { return $null }
    $raw = kubectl get --raw "/api/v1/namespaces/$Namespace/pods/${pod}:2000/proxy/quicktunnel" 2>$null
    if (-not $raw) { return $null }
    $hostname = ($raw | ConvertFrom-Json).hostname
    if ($hostname) { return "https://$hostname" }
    return $null
}

$deadline = (Get-Date).AddMinutes(2)
do {
    $url = Get-TunnelUrl
    if ($url) {
        Write-Output $url
        exit 0
    }
    if ($Wait) { Start-Sleep -Seconds 3 }
} while ($Wait -and (Get-Date) -lt $deadline)

Write-Error "No quick tunnel URL yet. Check: kubectl -n $Namespace get pods -l $selector"
exit 1
