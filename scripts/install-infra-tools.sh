#!/usr/bin/env bash
# Linux amd64 tools. Verify extracted executables against reviewed SHA-256 hashes.
set -euo pipefail
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'Linux amd64 required' >&2; exit 1; }
destination=${1:-/tmp/voyage-tools}
mkdir -p "$destination"
destination=$(cd "$destination" && pwd)
workspace=$(mktemp -d)
trap 'rm -rf "$workspace"' EXIT
install_archive() {
  local name=$1 url=$2 member=$3 checksum=$4
  curl --fail --silent --show-error --location --retry 3 "$url" -o "$workspace/archive.tgz"
  tar -xzf "$workspace/archive.tgz" -C "$workspace" "$member"
  echo "$checksum  $workspace/$member" | sha256sum --check --status
  install -m 0755 "$workspace/$member" "$destination/$name"
}
install_archive helm https://get.helm.sh/helm-v3.19.0-linux-amd64.tar.gz linux-amd64/helm e4722a77de9df824214aaf19d43687c49f7cbcf3b107905acea002173777d486
install_archive actionlint https://github.com/rhysd/actionlint/releases/download/v1.7.7/actionlint_1.7.7_linux_amd64.tar.gz actionlint 9f7dedb4e23f89f2922073d1a6720405b7b520d4f5832ebb96f0d55a2958886c
install_archive kubeconform https://github.com/yannh/kubeconform/releases/download/v0.7.0/kubeconform-linux-amd64.tar.gz kubeconform dd5273bdbf08531bf230f4eba8359984b7beec25a679424ff90911a2591b8b0d
curl --fail --silent --show-error --location --retry 3 https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-amd64 -o "$workspace/kind"
echo "517ab7fc89ddeed5fa65abf71530d90648d9638ef0c4cde22c2c11f8097b8889  $workspace/kind" | sha256sum --check --status
install -m 0755 "$workspace/kind" "$destination/kind"
echo "Tools installed to $destination. Add it to PATH."
