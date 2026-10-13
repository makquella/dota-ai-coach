// Direct publishing for the promo engine (docs/MARKETING_ENGINE.md): YouTube
// (Data API v3), Instagram (Instagram API with Instagram Login) and TikTok
// (Content Posting API). Each network exposes the same small interface:
//
//   authUrl(env, redirect, state)          the consent page the bot links to
//   exchange(env, code, redirect, now)     the code -> an account {tokens, id, name}
//   fresh(env, account, now)               the account with a usable access token
//   step(env, account, job, now)           one step of a delivery -> {status, ...}
//   stats(env, account, items)             numbers of published videos
//
// A delivery is a small state machine run by the five-minute cron: 'queued'
// -> 'processing' (Instagram builds the Reel, TikTok checks the upload) ->
// 'published' | 'draft' (TikTok inbox) | 'error'. Steps never publish twice:
// the external id is stored after the first call and only polled after that.

export const SOCIAL_NETWORKS = ["youtube", "instagram", "tiktok"];
export const NETWORK_NAMES = { youtube: "YouTube", instagram: "Instagram", tiktok: "TikTok" };
export const NETWORK_SECRETS = {
  youtube: ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"],
  instagram: ["INSTAGRAM_APP_ID", "INSTAGRAM_APP_SECRET"],
  tiktok: ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"]
};
const TIKTOK_CHUNK_MAX = 64 * 1024 * 1024; // one chunk up to 64 MB
const IG = "https://graph.instagram.com/v21.0";
const TT = "https://open.tiktokapis.com";

export function socialConfigured(env, network) {
  return (NETWORK_SECRETS[network] || []).every((name) => String(env[name] || "").trim());
}

function secret(env, name) {
  return String(env[name] || "").trim();
}

async function answer(response) {
  const raw = await response.text();
  try {
    return { ok: response.ok, status: response.status, data: raw ? JSON.parse(raw) : {}, headers: response.headers };
  } catch {
    return { ok: response.ok, status: response.status, data: { raw: raw.slice(0, 300) }, headers: response.headers };
  }
}

function form(values) {
  return new URLSearchParams(Object.entries(values).filter(([, v]) => v !== undefined && v !== null));
}

function problem(result, fallback) {
  const d = result.data || {};
  const message =
    d.error?.message || d.error_description || d.error?.code || d.error_message || d.message || d.raw || fallback;
  return `${result.status} ${String(typeof message === "string" ? message : JSON.stringify(message)).slice(0, 240)}`;
}

// --- sealed tokens ----------------------------------------------------------------------

async function sealKey(env) {
  const admin = secret(env, "ADMIN_TOKEN");
  if (!admin) throw new Error("ADMIN_TOKEN is needed to store tokens");
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`wardly-promo-tokens:${admin}`));
  return crypto.subtle.importKey("raw", digest, "AES-GCM", false, ["encrypt", "decrypt"]);
}

function b64(bytes) {
  let s = "";
  for (const b of new Uint8Array(bytes)) s += String.fromCharCode(b);
  return btoa(s);
}

function unb64(text) {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
}

export async function seal(env, value) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = new TextEncoder().encode(JSON.stringify(value));
  const sealed = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await sealKey(env), data);
  return `v1.${b64(iv)}.${b64(sealed)}`;
}

export async function unseal(env, text) {
  const [version, iv, data] = String(text || "").split(".");
  if (version !== "v1" || !iv || !data) throw new Error("bad sealed value");
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(iv) }, await sealKey(env), unb64(data));
  return JSON.parse(new TextDecoder().decode(plain));
}

// --- YouTube ----------------------------------------------------------------------------

const youtube = {
  authUrl(env, redirect, state) {
    const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    url.search = form({
      client_id: secret(env, "YOUTUBE_CLIENT_ID"),
      redirect_uri: redirect,
      response_type: "code",
      scope: "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
      access_type: "offline",
      prompt: "consent",
      include_granted_scopes: "true",
      state
    }).toString();
    return url.toString();
  },

  async exchange(env, code, redirect, now) {
    const token = await answer(
      await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        body: form({
          code,
          client_id: secret(env, "YOUTUBE_CLIENT_ID"),
          client_secret: secret(env, "YOUTUBE_CLIENT_SECRET"),
          redirect_uri: redirect,
          grant_type: "authorization_code"
        })
      })
    );
    if (!token.ok || !token.data.refresh_token) throw new Error(`YouTube token: ${problem(token, "no refresh token")}`);
    const account = {
      access_token: token.data.access_token,
      refresh_token: token.data.refresh_token,
      expires_at: now + (token.data.expires_in || 3600) * 1000
    };
    const channel = await answer(
      await fetch("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true", {
        headers: { authorization: `Bearer ${account.access_token}` }
      })
    );
    const item = channel.data.items?.[0];
    return { ...account, id: item?.id || null, name: item?.snippet?.title || "YouTube" };
  },

  async fresh(env, account, now) {
    if (account.access_token && account.expires_at > now + 120_000) return { account, changed: false };
    const token = await answer(
      await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        body: form({
          client_id: secret(env, "YOUTUBE_CLIENT_ID"),
          client_secret: secret(env, "YOUTUBE_CLIENT_SECRET"),
          refresh_token: account.refresh_token,
          grant_type: "refresh_token"
        })
      })
    );
    if (!token.ok) throw new Error(`YouTube refresh: ${problem(token, "refresh failed")}`);
    return {
      account: { ...account, access_token: token.data.access_token, expires_at: now + (token.data.expires_in || 3600) * 1000 },
      changed: true
    };
  },

  async step(env, account, job) {
    const privacy = ["public", "unlisted", "private"].includes(String(env.YOUTUBE_PRIVACY)) ? env.YOUTUBE_PRIVACY : "public";
    const meta = {
      snippet: {
        title: job.body.youtube_title,
        description: `${job.body.caption}`.slice(0, 4900),
        categoryId: "20", // Gaming
        tags: ["dota 2", "дота 2", "wardly", "dota2"],
        defaultLanguage: "uk"
      },
      status: { privacyStatus: privacy, selfDeclaredMadeForKids: false, embeddable: true }
    };
    const init = await answer(
      await fetch("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", {
        method: "POST",
        headers: {
          authorization: `Bearer ${account.access_token}`,
          "content-type": "application/json; charset=UTF-8",
          "x-upload-content-length": String(job.media.size),
          "x-upload-content-type": "video/mp4"
        },
        body: JSON.stringify(meta)
      })
    );
    const location = init.headers?.get("location");
    if (!init.ok || !location) return { status: "retry", detail: `YouTube upload: ${problem(init, "no upload URL")}` };
    const video = await job.media.open();
    const uploaded = await answer(
      await fetch(location, {
        method: "PUT",
        headers: { "content-type": "video/mp4", "content-length": String(job.media.size) },
        body: video
      })
    );
    if (!uploaded.ok || !uploaded.data.id) return { status: "retry", detail: `YouTube upload: ${problem(uploaded, "no video id")}` };
    const got = uploaded.data.status?.privacyStatus;
    return {
      status: "published",
      external_id: uploaded.data.id,
      url: `https://youtube.com/shorts/${uploaded.data.id}`,
      detail: got && got !== privacy ? `YouTube зробив відео ${got} (проєкт API ще не пройшов аудит)` : null
    };
  },

  async stats(env, account, items) {
    if (!items.length) return [];
    const ids = items.map((i) => i.external_id).join(",");
    const result = await answer(
      await fetch(`https://www.googleapis.com/youtube/v3/videos?part=statistics&id=${encodeURIComponent(ids)}`, {
        headers: { authorization: `Bearer ${account.access_token}` }
      })
    );
    if (!result.ok) return [];
    return (result.data.items || []).map((v) => ({
      external_id: v.id,
      views: Number(v.statistics?.viewCount) || 0,
      likes: Number(v.statistics?.likeCount) || 0,
      comments: Number(v.statistics?.commentCount) || 0,
      shares: 0
    }));
  }
};

// --- Instagram (Reels) ------------------------------------------------------------------

const IG_REFRESH_AFTER = 7 * 86_400_000; // long-lived tokens last 60 days; refresh weekly

const instagram = {
  authUrl(env, redirect, state) {
    const url = new URL("https://www.instagram.com/oauth/authorize");
    url.search = form({
      enable_fb_login: "0",
      client_id: secret(env, "INSTAGRAM_APP_ID"),
      redirect_uri: redirect,
      response_type: "code",
      scope: "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_insights",
      state
    }).toString();
    return url.toString();
  },

  async exchange(env, code, redirect, now) {
    const short = await answer(
      await fetch("https://api.instagram.com/oauth/access_token", {
        method: "POST",
        body: form({
          client_id: secret(env, "INSTAGRAM_APP_ID"),
          client_secret: secret(env, "INSTAGRAM_APP_SECRET"),
          grant_type: "authorization_code",
          redirect_uri: redirect,
          code: code.replace(/#_$/, "")
        })
      })
    );
    const first = short.data.data?.[0] || short.data;
    if (!short.ok || !first.access_token) throw new Error(`Instagram token: ${problem(short, "no token")}`);
    const long = await answer(
      await fetch(
        `https://graph.instagram.com/access_token?${form({
          grant_type: "ig_exchange_token",
          client_secret: secret(env, "INSTAGRAM_APP_SECRET"),
          access_token: first.access_token
        })}`
      )
    );
    if (!long.ok || !long.data.access_token) throw new Error(`Instagram long-lived token: ${problem(long, "no token")}`);
    const token = long.data.access_token;
    const me = await answer(await fetch(`${IG}/me?${form({ fields: "user_id,username", access_token: token })}`));
    return {
      access_token: token,
      refreshed_at: now,
      expires_at: now + (long.data.expires_in || 5_184_000) * 1000,
      id: String(me.data.user_id || first.user_id || ""),
      name: me.data.username ? `@${me.data.username}` : "Instagram"
    };
  },

  async fresh(env, account, now) {
    if (now - (account.refreshed_at || 0) < IG_REFRESH_AFTER) return { account, changed: false };
    const result = await answer(
      await fetch(
        `https://graph.instagram.com/refresh_access_token?${form({ grant_type: "ig_refresh_token", access_token: account.access_token })}`
      )
    );
    if (!result.ok || !result.data.access_token) {
      // Still valid until it expires: keep it, try again on the next run.
      if (account.expires_at > now) return { account, changed: false };
      throw new Error(`Instagram refresh: ${problem(result, "refresh failed")}`);
    }
    return {
      account: {
        ...account,
        access_token: result.data.access_token,
        refreshed_at: now,
        expires_at: now + (result.data.expires_in || 5_184_000) * 1000
      },
      changed: true
    };
  },

  async step(env, account, job) {
    const token = account.access_token;
    if (!job.external_id) {
      const created = await answer(
        await fetch(`${IG}/${account.id}/media`, {
          method: "POST",
          body: form({
            media_type: "REELS",
            video_url: job.media.url,
            cover_url: job.media.cover_url || undefined,
            caption: job.body.caption,
            share_to_feed: "true",
            access_token: token
          })
        })
      );
      if (!created.ok || !created.data.id) return { status: "retry", detail: `Instagram: ${problem(created, "no container")}` };
      return { status: "processing", external_id: String(created.data.id), retry_in: 60_000 };
    }
    const container = await answer(
      await fetch(`${IG}/${job.external_id}?${form({ fields: "status_code,status", access_token: token })}`)
    );
    const code = container.data.status_code;
    if (code === "IN_PROGRESS" || (!container.ok && container.status >= 500)) {
      return { status: "processing", external_id: job.external_id, retry_in: 60_000 };
    }
    if (code !== "FINISHED") {
      return { status: "error", external_id: job.external_id, detail: `Instagram: ${code || problem(container, "status")} ${container.data.status || ""}`.trim() };
    }
    const published = await answer(
      await fetch(`${IG}/${account.id}/media_publish`, {
        method: "POST",
        body: form({ creation_id: job.external_id, access_token: token })
      })
    );
    if (!published.ok || !published.data.id) return { status: "retry", external_id: job.external_id, detail: `Instagram publish: ${problem(published, "no media id")}` };
    const media = await answer(await fetch(`${IG}/${published.data.id}?${form({ fields: "permalink", access_token: token })}`));
    return { status: "published", external_id: String(published.data.id), url: media.data.permalink || null, published: true };
  },

  async stats(env, account, items) {
    const out = [];
    for (const item of items) {
      const insights = await answer(
        await fetch(
          `${IG}/${item.external_id}/insights?${form({ metric: "views,likes,comments,shares", access_token: account.access_token })}`
        )
      );
      if (!insights.ok) continue;
      const value = (name) => {
        const metric = (insights.data.data || []).find((m) => m.name === name);
        return Number(metric?.values?.[0]?.value ?? metric?.total_value?.value) || 0;
      };
      out.push({ external_id: item.external_id, views: value("views"), likes: value("likes"), comments: value("comments"), shares: value("shares") });
    }
    return out;
  }
};

// --- TikTok -----------------------------------------------------------------------------

const tiktok = {
  authUrl(env, redirect, state) {
    const direct = String(env.TIKTOK_MODE || "inbox") === "direct";
    const url = new URL("https://www.tiktok.com/v2/auth/authorize/");
    url.search = form({
      client_key: secret(env, "TIKTOK_CLIENT_KEY"),
      response_type: "code",
      scope: ["user.info.basic", "video.list", "video.upload", ...(direct ? ["video.publish"] : [])].join(","),
      redirect_uri: redirect,
      state
    }).toString();
    return url.toString();
  },

  async exchange(env, code, redirect, now) {
    const token = await answer(
      await fetch(`${TT}/v2/oauth/token/`, {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded" },
        body: form({
          client_key: secret(env, "TIKTOK_CLIENT_KEY"),
          client_secret: secret(env, "TIKTOK_CLIENT_SECRET"),
          code,
          grant_type: "authorization_code",
          redirect_uri: redirect
        })
      })
    );
    if (!token.ok || !token.data.access_token) throw new Error(`TikTok token: ${problem(token, "no token")}`);
    const account = {
      access_token: token.data.access_token,
      refresh_token: token.data.refresh_token,
      expires_at: now + (token.data.expires_in || 86_400) * 1000,
      id: token.data.open_id || null
    };
    const info = await answer(
      await fetch(`${TT}/v2/user/info/?fields=open_id,display_name`, { headers: { authorization: `Bearer ${account.access_token}` } })
    );
    return { ...account, name: info.data.data?.user?.display_name || "TikTok" };
  },

  async fresh(env, account, now) {
    if (account.access_token && account.expires_at > now + 300_000) return { account, changed: false };
    const token = await answer(
      await fetch(`${TT}/v2/oauth/token/`, {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded" },
        body: form({
          client_key: secret(env, "TIKTOK_CLIENT_KEY"),
          client_secret: secret(env, "TIKTOK_CLIENT_SECRET"),
          grant_type: "refresh_token",
          refresh_token: account.refresh_token
        })
      })
    );
    if (!token.ok || !token.data.access_token) throw new Error(`TikTok refresh: ${problem(token, "refresh failed")}`);
    return {
      account: {
        ...account,
        access_token: token.data.access_token,
        refresh_token: token.data.refresh_token || account.refresh_token,
        expires_at: now + (token.data.expires_in || 86_400) * 1000
      },
      changed: true
    };
  },

  async step(env, account, job) {
    const auth = { authorization: `Bearer ${account.access_token}`, "content-type": "application/json; charset=UTF-8" };
    if (!job.external_id) {
      const size = job.media.size;
      if (size > TIKTOK_CHUNK_MAX) return { status: "error", detail: "TikTok: відео більше 64 МБ" };
      const source_info = { source: "FILE_UPLOAD", video_size: size, chunk_size: size, total_chunk_count: 1 };
      let path = "/v2/post/publish/inbox/video/init/";
      let body = { source_info };
      if (String(env.TIKTOK_MODE || "inbox") === "direct") {
        const creator = await answer(await fetch(`${TT}/v2/post/publish/creator_info/query/`, { method: "POST", headers: auth }));
        const options = creator.data.data?.privacy_level_options || [];
        const privacy = options.includes("PUBLIC_TO_EVERYONE") ? "PUBLIC_TO_EVERYONE" : options[0] || "SELF_ONLY";
        path = "/v2/post/publish/video/init/";
        body = {
          post_info: {
            title: job.body.caption.slice(0, 2200),
            privacy_level: privacy,
            disable_duet: false,
            disable_comment: false,
            disable_stitch: false,
            brand_content_toggle: false,
            brand_organic_toggle: true
          },
          source_info
        };
      }
      const init = await answer(await fetch(`${TT}${path}`, { method: "POST", headers: auth, body: JSON.stringify(body) }));
      const data = init.data.data || {};
      if (!init.ok || !data.upload_url || !data.publish_id) return { status: "retry", detail: `TikTok: ${problem(init, "no upload URL")}` };
      const video = await job.media.open();
      const put = await fetch(data.upload_url, {
        method: "PUT",
        headers: {
          "content-type": "video/mp4",
          "content-length": String(size),
          "content-range": `bytes 0-${size - 1}/${size}`
        },
        body: video
      });
      if (!put.ok) return { status: "retry", detail: `TikTok upload: ${put.status}` };
      return { status: "processing", external_id: data.publish_id, retry_in: 60_000 };
    }
    const status = await answer(
      await fetch(`${TT}/v2/post/publish/status/fetch/`, {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ publish_id: job.external_id })
      })
    );
    const data = status.data.data || {};
    if (data.status === "SEND_TO_USER_INBOX") {
      return { status: "draft", external_id: job.external_id, detail: "TikTok: чернетка у «Вхідних» застосунку — опублікуйте її там" };
    }
    if (data.status === "PUBLISH_COMPLETE") {
      const id = data.publicaly_available_post_id?.[0];
      return { status: "published", external_id: id ? String(id) : job.external_id, url: id ? `https://www.tiktok.com/video/${id}` : null };
    }
    if (data.status === "FAILED") return { status: "error", external_id: job.external_id, detail: `TikTok: ${data.fail_reason || "failed"}` };
    return { status: "processing", external_id: job.external_id, retry_in: 60_000 };
  },

  async stats(env, account, items) {
    const list = await answer(
      await fetch(`${TT}/v2/video/list/?fields=id,title,video_description,share_url,view_count,like_count,comment_count,share_count`, {
        method: "POST",
        headers: { authorization: `Bearer ${account.access_token}`, "content-type": "application/json" },
        body: JSON.stringify({ max_count: 20 })
      })
    );
    if (!list.ok) return [];
    const videos = list.data.data?.videos || [];
    const out = [];
    for (const item of items) {
      const first = String(item.caption || "").split("\n")[0].trim().slice(0, 40).toLowerCase();
      const video =
        videos.find((v) => String(v.id) === String(item.external_id)) ||
        videos.find((v) => {
          const text = String(v.video_description || v.title || "").toLowerCase();
          return first && text && (text.startsWith(first) || (text.length >= 20 && first.startsWith(text)));
        });
      if (video) {
        out.push({
          external_id: item.external_id,
          url: video.share_url || null,
          views: Number(video.view_count) || 0,
          likes: Number(video.like_count) || 0,
          comments: Number(video.comment_count) || 0,
          shares: Number(video.share_count) || 0
        });
      }
    }
    return out;
  }
};

export const NETWORK_CLIENTS = { youtube, instagram, tiktok };

// --- stored accounts --------------------------------------------------------------------

export async function loadAccount(env, network) {
  const row = await env.DB.prepare("SELECT sealed FROM promo_accounts WHERE network = ?1").bind(network).first();
  return row ? unseal(env, row.sealed) : null;
}

export async function saveAccount(env, network, account, now = Date.now()) {
  await env.DB.prepare(
    "INSERT INTO promo_accounts (network, sealed, account, updated_at) VALUES (?1, ?2, ?3, ?4) " +
      "ON CONFLICT (network) DO UPDATE SET sealed = ?2, account = ?3, updated_at = ?4"
  )
    .bind(network, await seal(env, account), account.name || null, now)
    .run();
}

export async function connectedNetworks(env) {
  const { results } = await env.DB.prepare("SELECT network, account, updated_at FROM promo_accounts").all();
  return Object.fromEntries((results || []).map((r) => [r.network, { name: r.account, updated_at: r.updated_at }]));
}
