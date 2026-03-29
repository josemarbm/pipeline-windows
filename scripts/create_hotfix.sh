#!/bin/bash
set -e

message() {
  echo -e "\n######################################################################"
  echo "# $1"
  echo "######################################################################"
}
sleep 3
getHotfixReleaseVersion() {
  # 1. Create array based on LATEST_TAG
  # Get the latest semantic version tag, ignoring CI sha tags
  LATEST_TAG=$(git tag --list "v[0-9]*" --sort=-v:refname | head -n 1)

  if [[ -z "$LATEST_TAG" ]]; then
    echo "No valid version tags found. Cannot create hotfix."
    exit 1
  fi

  # Remove 'v' prefix and split by dots
  VERSION_NO_V="${LATEST_TAG#v}"
  TAG_LIST=($(echo "$VERSION_NO_V" | tr '.' ' '))

  # 2. Exit if invalid version
  [[ "${#TAG_LIST[@]}" -lt 2 ]] && echo "$LATEST_TAG is not a valid version" && exit 1

  # 3. Calculate release version (Increment Minor)
  V_MAJOR=${TAG_LIST[0]}
  V_MINOR=$(( TAG_LIST[1] + 1 ))
  RELEASE_VERSION=${V_MAJOR}.${V_MINOR}
  sleep 3
}

message ">>> Starting hotfix"

[[ ! -x "$(command -v gh)" ]] && echo "gh not found, you need to install github CLI" && exit 1

gh auth status

# 1. Make sure branch is set to main
[[ $(git rev-parse --abbrev-ref HEAD) != "main" ]] && echo "ERROR: Checkout to main" && exit 1

# 2. Make sure branch is clean
[[ $(git status --porcelain) ]] && echo "ERROR: The branch is not clean, commit your changes before creating the release" && exit 1

message ">>> Pulling main"
git pull origin main
message ">>> Pulling tags"
git fetch --prune --tags

getHotfixReleaseVersion

message ">>> Hotfix: $RELEASE_VERSION"

# 3. Start hotfix
read -r -p "What is the name of the branch you want to create (should start with hotfix/):  " BRANCH_NAME
[[ $BRANCH_NAME != hotfix/* ]] && echo "'$BRANCH_NAME' is invalid, it should start with 'hotfix/')" && exit 1

read -r -p "Are you sure you want to create the branch '$BRANCH_NAME' [Y/n]:  " RESPONSE
if [[ $RESPONSE =~ ^([yY][eE][sS]|[yY])$ ]]; then

  message ">>>>> Creating branch '$BRANCH_NAME' from main..."
  git checkout -b "$BRANCH_NAME" main
  git commit --allow-empty -m "Hotfix - $RELEASE_VERSION"
  git push origin "$BRANCH_NAME"
  gh pr create --base main --head "$BRANCH_NAME" --title "Hotfix - $RELEASE_VERSION" --fill
  sleep 5
else

  message "Action cancelled exiting..."
  exit 1

fi
sleep 10