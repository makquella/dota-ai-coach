# Markdown retrieval cache (0.53.45)

The application's `KnowledgeBaseCache` owns an immutable tuple of parsed
paragraphs. Lifespan warms it on a worker before serving requests. Packaged
resources retain that catalog for the process lifetime; source checkouts inspect
sorted Markdown path/mtime-ns/size signatures. Unchanged signatures do no content
reads or parsing. Added/deleted/edited documents refresh the catalog.

The first concurrent lookups share one load. File reads run outside the cache
condition; during later refreshes readers keep the previous complete catalog.
Publication verifies the file signature after all reads. A changing signature
retries once; repeat changes or filesystem/UTF-8 failure preserve the previous
catalog (or return empty context on first failure), record only the error type,
and wait one second before another lookup attempts I/O. Metadata-based development
invalidation cannot detect edits deliberately preserving both mtime and size.

`/diagnostics.knowledge_base` exposes loading, successful catalog loads, complete
file reads (including a discarded attempt), paragraph count, failures and safe
last error. It retains no document names/content. There is no background queue,
external retrieval service or vector database. This bounds retries, not OS I/O
time. A fallback catalog after refresh failure may be older; health records that
failure instead of presenting it as a fresh read.

Scheduler `evaluate` accepts the existing list argument or a lazy context callable.
Live/demo pass a callable, executed once outside the scheduler owner only after
no-advice/duplicate/cooldown/low-HP early returns. Later UX/spacing policy may still
suppress a generated candidate; those paths require candidate text and therefore
may retrieve context. Direct `/recommend` still retrieves immediately. Accepted
advice logs and optional live LLM receive the same resolved paragraphs.

Real-file/HTTP tests cover unchanged lookup, edit/add/delete, packaged behavior,
bad UTF-8 plus retry backoff, concurrent initial reads, complete old-catalog reads
during refresh, changed-file verification/retry, owned-item filtering, detached
results, and zero retrieval calls on actual early duplicate live/demo responses.
Existing deterministic policy, scheduler spacing and replay tests remain required.
