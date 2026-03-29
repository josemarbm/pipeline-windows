#!/bin/bash
set -e

message() {
  echo -e "\n######################################################################"
  echo "# $1"
  echo "######################################################################"
}
getReleaseVersion() {
  # 1. Create array based on LATEST_TAG
  # Get the latest semantic version tag, ignoring CI sha tags
  LATEST_TAG=$(git tag --list "v[0-9]*" --sort=-v:refname | head -n 1)
  
  if [[ -z "$LATEST_TAG" ]]; then
    echo "No valid version tags found. Assuming v1.0"
    RELEASE_VERSION="1.0"
    return
  fi

  # Remove 'v' prefix and split by dots
  VERSION_NO_V="${LATEST_TAG#v}"
  TAG_LIST=($(echo "$VERSION_NO_V" | tr '.' ' '))

  # 2. Exit if invalid version
  [[ "${#TAG_LIST[@]}" -lt 2 ]] && echo "$LATEST_TAG is not a valid version" && exit 1

  # 3. Calculate release version (Increment Major)
  V_MAJOR=$(( TAG_LIST[0] + 1 ))
  V_MINOR=0
  V_PATCH=0
  RELEASE_VERSION=${V_MAJOR}.${V_MINOR}.${V_PATCH}
}

message ">>> Starting release"

[[ ! -x "$(command -v gh)" ]] && echo "gh not found, you need to install github CLI" && exit 1

gh auth status

# 1. Make sure branch is set to main
[[ $(git rev-parse --abbrev-ref HEAD) != "main" ]] && echo "ERROR: Checkout to main" && exit 1

# 2. Make sure branch is clean
[[ $(git status --porcelain) ]] && echo "ERROR: The branch is not clean, commit your changes before creating the release" && exit 1

message ">>> Pulling main"
git pull origin main ##
message ">>> Pulling tags"
git fetch --prune --prune-tags origin

getReleaseVersion

message ">>> Release: $RELEASE_VERSION"

# 5. Start release
read -r -p "Last release version was '$LATEST_TAG', do you want to create '$RELEASE_VERSION' [Y/n]:  " RESPONSE
if [[ $RESPONSE =~ ^([yY][eE][sS]|[yY])$ ]]; then

  # Remove os pontos da versão para a branch
  BRANCH_SAFE_VERSION="${RELEASE_VERSION//./-}"
  BRANCH_NAME="release/$BRANCH_SAFE_VERSION"
  message ">>>>> Creating branch '$BRANCH_NAME' from main..."

  git checkout -b "$BRANCH_NAME" main
  git push origin "$BRANCH_NAME"
  gh pr create --base main --head "$BRANCH_NAME" --title "Release - $RELEASE_VERSION" --fill

else

    message "Action cancelled exiting..."
    exit 1

fi
