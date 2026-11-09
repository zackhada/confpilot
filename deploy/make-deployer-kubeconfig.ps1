<#
.SYNOPSIS
  Writes a kubeconfig for the `deployer` ServiceAccount, for the KUBE_CONFIG secret of the
  `production` GitHub environment.
.DESCRIPTION
  Run with an admin kubectl context on the confpilot cluster, after
  `kubectl apply -k deploy/k8s` has created deploy/k8s/deployer-rbac.yaml.
  The file holds a long-lived credential: it is written outside the repo by default, never
  printed, and should be deleted once the secret is set.
.EXAMPLE
  deploy/make-deployer-kubeconfig.ps1
  Get-Content -Raw $env:TEMP\confpilot-deployer.kubeconfig | gh secret set KUBE_CONFIG --env production --repo zackhada/confpilot
#>
[CmdletBinding()]
param(
    [string]$Namespace = 'confpilot',
    [string]$OutFile = (Join-Path $env:TEMP 'confpilot-deployer.kubeconfig')
)

$ErrorActionPreference = 'Stop'

function Get-KubectlValue {
    $value = kubectl @args
    if ($LASTEXITCODE -ne 0 -or -not $value) { throw "kubectl $($args -join ' ') returned nothing" }
    return $value
}

$server = Get-KubectlValue config view --minify --raw -o 'jsonpath={.clusters[0].cluster.server}'
$caData = Get-KubectlValue -n $Namespace get secret deployer-token -o 'jsonpath={.data.ca\.crt}'
$tokenB64 = Get-KubectlValue -n $Namespace get secret deployer-token -o 'jsonpath={.data.token}'
$token = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($tokenB64))

$kubeconfig = @"
apiVersion: v1
kind: Config
clusters:
  - name: confpilot
    cluster:
      server: $server
      certificate-authority-data: $caData
users:
  - name: deployer
    user:
      token: $token
contexts:
  - name: deployer@confpilot
    context:
      cluster: confpilot
      namespace: $Namespace
      user: deployer
current-context: deployer@confpilot
"@

# UTF-8 without a BOM and with LF endings, so it pastes cleanly into a GitHub secret.
[IO.File]::WriteAllText($OutFile, ($kubeconfig -replace "`r`n", "`n") + "`n", [Text.UTF8Encoding]::new($false))

$canPatch = kubectl --kubeconfig $OutFile auth can-i patch deployment/confpilot
$canReadSecrets = kubectl --kubeconfig $OutFile auth can-i get secrets
Write-Host "Wrote $OutFile"
Write-Host "  can patch deployment/confpilot: $canPatch (expected yes)"
Write-Host "  can read secrets:               $canReadSecrets (expected no)"
Write-Host 'Next (repo admin): store the file content as the KUBE_CONFIG secret of the production environment, then delete the file.'
Write-Host "  Get-Content -Raw '$OutFile' | gh secret set KUBE_CONFIG --env production --repo zackhada/confpilot"
