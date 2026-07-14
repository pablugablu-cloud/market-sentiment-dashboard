# Keep the Streamlit Community Cloud app awake.
#
# Place this file at:  .github/workflows/keep-awake.yml
# in the SAME GitHub repo that Streamlit Cloud deploys from.
#
# How it works: Streamlit Community Cloud puts apps to sleep after a period
# with no visits. This workflow visits the app on a schedule so it always
# counts as "active".
#
# Two important caveats:
#   1. GitHub automatically disables scheduled workflows in repos with no
#      commit activity for ~60 days. Any commit (even editing this file)
#      re-enables it. If your repo is dormant, prefer UptimeRobot (below).
#   2. If a plain HTTP GET ever stops registering as activity (Streamlit
#      has changed this behavior before), switch to the UptimeRobot option
#      or the headless-browser step commented out at the bottom.

name: Keep Streamlit app awake

on:
  schedule:
    # Every 4 hours — well inside Streamlit's inactivity window.
    - cron: "0 */4 * * *"
  workflow_dispatch: {}   # lets you trigger it manually from the Actions tab

permissions: {}

jobs:
  ping:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Ping the app
        run: |
          set -e
          URL="https://masenti.streamlit.app/"
          CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
                 --max-time 90 --retry 3 --retry-delay 15 --retry-all-errors \
                 -A "keep-awake-bot" "$URL")
          echo "Pinged $URL — HTTP $CODE"
          # 200 = awake. 303/307 can appear while the app is waking up; the
          # request itself is what wakes it, so treat those as success too.
          case "$CODE" in
            2*|303|307) exit 0 ;;
            *) echo "Unexpected status $CODE"; exit 1 ;;
          esac

      # --- Fallback: real browser visit (uncomment if plain GET stops working) ---
      # - uses: actions/setup-node@v4
      #   with: { node-version: 20 }
      # - name: Wake with a real browser
      #   run: |
      #     npx --yes playwright install --with-deps chromium
      #     npx --yes playwright@latest cr https://masenti.streamlit.app/ || true
