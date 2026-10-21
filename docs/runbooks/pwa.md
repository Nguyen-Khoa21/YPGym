# YPGym web PWA runbook

YPGym's React website is a PWA-capable web application. It remains separate from the Expo mobile application.

## Implementation

- `vite-plugin-pwa` 2.0.0 generates the production service worker and Workbox precache manifest. This release supports Vite 7 and avoids maintaining a custom service-worker build pipeline.
- `workbox-window` 7.4.1 is declared directly because the plugin's official React update-prompt integration requires it.
- Vite remains on major version 7 and is patched to 7.3.7 to resolve the Windows `launch-editor` command-injection advisories without introducing a Vite 8 migration.
- The existing `manifest.webmanifest` remains authoritative. The plugin does not replace it.
- Development service-worker generation is disabled to prevent stale-cache confusion while using `npm run dev`.
- Production builds precache only the generated application shell, versioned JavaScript/CSS, HTML, icons, SVG and the manifest.
- Every YPGym `/api/**` request uses `NetworkOnly` for GET, POST, PUT, PATCH and DELETE. Authentication, OAuth, QR, attendance, VNPay, account data and mutations are never written to Cache Storage.
- External provider pages are outside the service worker's origin and have no runtime cache rule.

The shell can open after one successful online visit. Private data and server actions still require the API, and the offline notice says so explicitly.

## Build and preview

```powershell
cd C:\Users\Admin\ypgym\frontend
npm ci
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

Open `http://localhost:4173`. A production build emits `dist/sw.js`, a versioned Workbox runtime, the application assets and the existing manifest.

## Install and offline check

1. Open the production preview on localhost or deploy it behind HTTPS.
2. In browser developer tools, open **Application → Manifest** and confirm the name, standalone display and 192/512 icons.
3. Open **Application → Service Workers** and confirm `sw.js` is activated.
4. Visit the login page once while online.
5. Enable browser offline mode and reload the login route.
6. Confirm that the saved shell renders with the offline notice.
7. Confirm that sign-in, QR, attendance, payment and API actions do not claim success while offline.
8. Under **Application → Cache Storage**, verify that entries contain static build assets only and no `/api/` URLs, tokens, payment responses or personal records.

## Update check

1. Keep the first production build open until its service worker is active.
2. Deploy or preview a second production build with changed application content.
3. Reload or ask the service-worker registration to check for updates.
4. Confirm that **YPGym update available** appears.
5. Choose **Later** and confirm the current page remains usable.
6. Trigger the update again, choose **Update now**, and confirm the page reloads into the new build.

The application does not activate a waiting worker without the user's action.

## Verification record

On October 21, 2026, the production build generated `sw.js` and a versioned Workbox runtime with 15 static precache entries. A Chromium production-preview check confirmed that the worker activated on localhost, the login shell reloaded offline, Cache Storage contained no `/api/` URL, and an offline API request was rejected. A two-build check confirmed the update prompt, **Later** dismissal, prompt restoration after reload, and **Update now** activation.

The repository does not install Lighthouse, so an automated Lighthouse score was not recorded (`npx --no-install lighthouse --version` reported that the package is unavailable). Run the browser's Application and Lighthouse panels against the final HTTPS deployment to record deployment-specific installability and PWA checks without adding Lighthouse to the application dependency tree.

## Clear local PWA state

For local troubleshooting, open browser developer tools and use **Application → Storage → Clear site data**, then unregister the service worker under **Application → Service Workers**. Reload the page online afterward.

Do not enable the development service worker as a workaround; use a production build and preview when testing PWA behavior.

## Dependency review

The October 21, 2026 install audit reports eight build-tool advisories in the existing Tailwind CSS 3 dependency chain. Npm proposes Tailwind 4 as the complete fix, which is a major styling migration and is outside this PWA slice. The generated service worker has no server runtime dependency on Tailwind. Review the Tailwind 4 migration separately rather than forcing it into this change.
