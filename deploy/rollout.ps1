<#
.SYNOPSIS
  Rolls a built image out to the confpilot Deployment and waits for it.
.DESCRIPTION
  Takes a tag of ghcr.io/zackhada/confpilot (a commit SHA, or `main`), or a full image
  reference. Uses whatever cluster your current kubectl context points at.
  If the new pod never becomes Ready the old one keeps serving; undo with -Undo.
.EXAMPLE
  deploy/rollout.ps1 3f2c1ab9d0e4...     # a commit SHA built by the Deploy workflow
  deploy/rollout.ps1 main                # re-pull the moving tag
  deploy/rollout.ps1 -Undo               # back to the previous revision
#>
[CmdletBinding(DefaultParameterSetName = 'Tag')]
param(
    [Parameter(Mandatory, Position = 0, ParameterSetName = 'Tag')]
    [ValidatePattern('^[A-Za-z0-9._:/@-]+$')]
    [string]$Tag,

    [Parameter(Mandatory, ParameterSetName = 'Undo')]
    [switch]$Undo,

    [string]$Namespace = 'confpilot',
    [string]$Repository = 'ghcr.io/zackhada/confpilot',
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
$deployment = 'deployment/confpilot'

function Invoke-Kubectl {
    kubectl @args
    if ($LASTEXITCODE -ne 0) { throw "kubectl $($args -join ' ') failed ($LASTEXITCODE)" }
}

if ($Undo) {
    Invoke-Kubectl -n $Namespace rollout undo $deployment
}
else {
    $image = if ($Tag -match '[/@]') { $Tag } else { "${Repository}:$Tag" }
    Write-Host "Rolling out $image to $(kubectl config current-context)"
    Invoke-Kubectl -n $Namespace set image $deployment "app=$image"
    if ($Tag -eq 'main') {
        # Same tag, so the pod template did not change; force a new pod to pull it.
        Invoke-Kubectl -n $Namespace rollout restart $deployment
    }
}

Invoke-Kubectl -n $Namespace rollout status $deployment "--timeout=${TimeoutSeconds}s"
Invoke-Kubectl -n $Namespace get pods -l app.kubernetes.io/name=confpilot -o wide
