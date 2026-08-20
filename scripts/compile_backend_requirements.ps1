$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mount = "type=bind,source=$repositoryRoot,target=/src"
$compile = @'
python -m pip install --disable-pip-version-check --quiet "pip-tools==7.6.1" &&
CUSTOM_COMPILE_COMMAND="powershell -File scripts/compile_backend_requirements.ps1" \
  pip-compile \
  --generate-hashes \
  --no-strip-extras \
  --resolver=backtracking \
  --output-file=backend/requirements.lock \
  backend/requirements.txt
'@

docker run --rm `
  --mount $mount `
  --workdir /src `
  python:3.14-slim `
  sh -c $compile

if ($LASTEXITCODE -ne 0) {
    throw "Backend requirements compilation failed with exit code $LASTEXITCODE."
}
