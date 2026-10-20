#!/usr/bin/env bash
# Local analysis only: downloads scanner tools/database; never uploads image layers.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo 'Usage: scan_release_image.sh IMAGE OUTPUT_DIRECTORY' >&2
  exit 2
fi
image="$1"
output_dir="$2"
mkdir -p "$output_dir"
tool_dir="$(mktemp -d)"
trap 'rm -rf "$tool_dir"' EXIT
install_scanner() {
  local tool="$1" version="$2" expected="$3"
  local asset="${tool}_${version}_linux_amd64.tar.gz"
  curl --fail --silent --show-error --location \
    "https://github.com/anchore/${tool}/releases/download/v${version}/${asset}" \
    --output "$tool_dir/$asset"
  echo "$expected  $tool_dir/$asset" | sha256sum --check --status
  tar -xzf "$tool_dir/$asset" -C "$tool_dir" "$tool"
}
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Release scanner requires Linux x86_64.' >&2
  exit 2
fi
install_scanner syft 1.55.0 bb65249542db5fedeeb4d3f9b018b75e7264dbfbbb10486f044581a92f90490d
install_scanner grype 0.121.0 64e07133d3486115de647a66581461dccf5c732748a0a3119077395565f15519
export SYFT_CHECK_FOR_APP_UPDATE=false GRYPE_CHECK_FOR_APP_UPDATE=false
"$tool_dir/syft" scan "$image" --platform linux/amd64 \
  --output "cyclonedx-json=$output_dir/sbom.json"
# No --only-fixed: unresolved High/Critical findings block even without a patch.
# Scanner/database failures also fail the release step.
"$tool_dir/grype" "sbom:$output_dir/sbom.json" \
  --fail-on high --output json > "$output_dir/vulnerabilities.json"
