/* The Worker entrypoint.

   This site is static and does not need one. It exists because Cloudflare
   treats a Worker with no script as "assets-only", and an assets-only Worker
   cannot have triggers: the Settings page hides Domains & Routes entirely,
   so there is no way to attach khaana.com to it. Adding a script makes it an
   ordinary Worker and the custom domain option comes back.

   It changes nothing about how the site is served. Static assets are matched
   first by default, so every real page, image and JSON file is still handled
   by the asset layer with the _headers rules applied, and this code never
   runs for them. It is reached only when nothing matched, which means a 404.

   That is worth something on its own: the site had no 404 page, so a mistyped
   URL returned an empty response.
*/
const NOT_FOUND = `<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Page not found | Khaana</title>
<link rel="stylesheet" href="/style.css" />
</head><body>
<section class="tight"><div class="container">
  <div class="eyebrow">404</div>
  <h1>That page is not here</h1>
  <p>The link may be old, or the address mistyped. The recipes are all still
     where they were.</p>
  <p><a class="find-cta" href="/cook.html">
       <span class="find-cta-label">Browse the recipes</span>
       <span class="find-cta-arrow" aria-hidden="true">&rarr;</span>
     </a></p>
</div></section>
</body></html>`;

export default {
  async fetch(request, env) {
    // Ask the asset layer first, against a neutral hostname.
    //
    // Passing `request` straight through fails with Cloudflare error 1042,
    // "Worker tried to fetch from another Worker on the same zone": the
    // request URL is this Worker's own host, so the binding call looks like
    // the Worker fetching itself and is refused. Every path on the site,
    // stylesheet included, returned 404 because of it. Only the path and
    // query matter to the asset lookup, so they are rehung on a host that is
    // not ours.
    const url = new URL(request.url);
    const asset = await env.ASSETS.fetch(
      new Request(new URL(url.pathname + url.search, 'https://assets.local'), request)
    );
    if (asset.status !== 404) return asset;

    return new Response(NOT_FOUND, {
      status: 404,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        // _headers does not apply to a response generated here, so the few
        // that matter are set by hand.
        'cache-control': 'public, max-age=0, must-revalidate',
        'x-content-type-options': 'nosniff',
        'referrer-policy': 'strict-origin-when-cross-origin'
      }
    });
  }
};
