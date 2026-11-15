# UI audit with a real browser

`audit.mjs` walks the site like a visitor, on a desktop and on a phone screen: every mission card, a site card,
the Earth ↔ Moon slider, the relief and highlight controls, the instrument filter, the vegetation filter, free
criteria (invalid input, then a real run), the browser Back button and shareable addresses. It records console
errors, blocked or failed requests, broken images, empty table cells and any sideways overflow, and takes
screenshots. Exit code 1 if a defect is found.

```bash
mkdir -p ~/tools/pw && cd ~/tools/pw && npm init -y && npm install --save-exact playwright@1.64.1
npx playwright install chromium
cp <repo>/tools/validation/ui-audit/audit.mjs . && node audit.mjs http://localhost:8080 ./shots
```

Playwright is not a dependency of the project: install it next to the script. On a machine without the
Chromium system libraries (and without sudo), download `libnspr4` and `libnss3` from a Debian mirror, extract
them with `dpkg -x` and point `LD_LIBRARY_PATH` at the extracted folder.
