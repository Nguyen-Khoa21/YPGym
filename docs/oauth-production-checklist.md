# OAuth production checklist

Application code and provider publication are separate gates. Local YPGym can be correct while Google Testing or Meta Development mode still limits who can sign in. Never copy client secrets into this document.

## Current status

| Gate | Status | Evidence or owner action |
|---|---|---|
| Local Google callback and code exchange | Verified locally | Backend validates Google OIDC claims, nonce and PKCE, then returns an opaque completion code. |
| Local Facebook callback and code exchange | Application path implemented | Live access remains limited by Meta app mode and roles until publication. |
| Existing-account guided linking | Implemented | Password and one-time verified-email confirmation are supported without email-only auto-linking. |
| Google public-user access | Pending owner action | Publish the production project's external audience after branding/domain review. |
| Meta public-user access | Pending owner action | Complete dashboard requirements and switch the production app to Live. |
| Production HTTPS deployment | Pending owner action | No production web/API domains are documented in this repository. |

## Environment separation

Use separate Google Cloud and Meta apps for development and production where practical. Keep localhost callbacks only in development credentials. Configure these variables independently without documenting their values:

- `FRONTEND_URL`
- `OAUTH_CALLBACK_BASE_URL`
- `GOOGLE_OAUTH_WEB_CLIENT_ID`
- `GOOGLE_OAUTH_WEB_CLIENT_SECRET`
- `FACEBOOK_APP_ID`
- `FACEBOOK_APP_SECRET`
- `FACEBOOK_GRAPH_API_VERSION`

YPGym rejects non-HTTPS frontend/callback URLs outside `development` and `test`, and rejects a provider configuration where only its ID or secret is present.

| Environment | Web origin | Callback base |
|---|---|---|
| Development | `http://localhost:5174` | `http://localhost:8001/api/v1` |
| Production | `https://<web-domain>` | `https://<api-domain>/api/v1` |

Production callback URIs are exactly:

```text
https://<api-domain>/api/v1/auth/oauth/google/callback
https://<api-domain>/api/v1/auth/oauth/facebook/callback
```

Replace placeholders with deployed hostnames. Do not add a trailing slash or mix staging and production domains.

## Google Cloud / Google Auth Platform

Development client:

1. Under **Google Auth Platform → Audience**, use **External → Testing** and add each permitted test Google account.
2. Under **Clients**, select the Web application client.
3. Add `http://localhost:5174` as an authorized JavaScript origin.
4. Add `http://localhost:8001/api/v1/auth/oauth/google/callback` as an authorized redirect URI.
5. Request only `openid`, `email`, and `profile`.

Production client:

1. Create/select a production Google Cloud project and Web application OAuth client.
2. Under **Branding**, configure app name, support email, developer contact, public homepage, privacy-policy URL, and terms URL.
3. Verify the production root domain in Google Search Console and add it under authorized domains.
4. Add only `https://<web-domain>` as an authorized JavaScript origin.
5. Add only `https://<api-domain>/api/v1/auth/oauth/google/callback` as an authorized redirect URI.
6. Under **Data Access**, retain only `openid`, `email`, and `profile`. Basic identity scopes do not themselves require sensitive/restricted-scope verification; branding/domain requirements can still apply.
7. Under **Audience**, choose **External** and publish **In production**. Testing permits only listed users and test authorizations can expire.
8. Complete any branding verification shown before claiming a verified YPGym name/logo.
9. Store the production client ID/secret using the variables above, restart the API, and verify `/api/v1/auth/providers` without printing values.

Official references: [OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect), [manage app audience](https://support.google.com/cloud/answer/15549945), [branding and authorized domains](https://support.google.com/cloud/answer/15549049), and [verification applicability](https://support.google.com/cloud/answer/13464323).

## Meta for Developers / Facebook Login

Development app:

1. Keep the local Meta app in Development mode.
2. Add Facebook Login; enable Client OAuth Login and Web OAuth Login.
3. Keep strict redirect matching enabled.
4. Use `http://localhost:8001/api/v1/auth/oauth/facebook/callback`. Meta may automatically permit localhost during Development mode.
5. Add each Facebook account as an app role/tester and have it accept the invitation.
6. Request only `public_profile` and `email`.

Production app:

1. Create/select the production Meta app and add the Facebook Login use case.
2. Configure the production app domain and website URL.
3. Add public privacy-policy and terms URLs, contact information, and user-data deletion instructions/callback.
4. Enable Client OAuth Login and Web OAuth Login with strict redirect matching.
5. Add exactly `https://<api-domain>/api/v1/auth/oauth/facebook/callback` under Valid OAuth Redirect URIs.
6. Request only `public_profile` and `email`. Complete App Review/business verification only when the dashboard requires it for the use case or additional permissions.
7. Complete required dashboard items, then switch the production app to Live. Development mode remains limited to roles/testers.
8. Store the production App ID/secret using the variables above, restart the API, and verify `/api/v1/auth/providers` without printing values.

Official reference: [Facebook Login](https://developers.facebook.com/docs/facebook-login/). Meta returned HTTP 429 to the documentation fetch used for this update, so confirm current dashboard labels before publishing.

## Manual acceptance matrix

Run each scenario for Google and Facebook in clean and normal browser profiles:

| Scenario | Expected result |
|---|---|
| New verified provider email | One member and identity; first attempt signs in; one security notice queued. |
| Previously linked identity | First attempt signs in; no duplicate records. |
| Existing local email, password proof | Guided page links once and signs in. |
| Existing local email, email proof | One-time email link connects once; reuse is rejected. |
| Logout and provider login | First attempt signs in. |
| Incognito provider login | First attempt signs in without prior local storage. |
| Consent denied | Friendly denial and safe retry path. |
| Expired/replayed callback | Stable error and no duplicate data. |
| Identity owned elsewhere | Safe conflict; no merge, transfer, or disclosure. |
| Unlink and relink | Confirmation appears; final usable method cannot be removed. |
| SMTP unavailable | Identity transaction remains committed; email retries without logging secrets. |
| Non-test/non-role account after publication | Works only after Google is In production or Meta is Live. |

Record deployed HTTPS origins, callbacks, publication state, test date, and tester initials without recording secrets or tokens.
