// YouTube may omit tags while a freshly uploaded video is still processing.
// A missing/transient metadata field is not accepted as a verified schedule.
export function scheduledVideoState(video, entry, channelId) {
  if (!video || video.snippet.channelId !== channelId) throw new Error('Scheduled video not found on the expected channel');
  if (video.status.privacyStatus !== 'private' || Date.parse(video.status.publishAt) !== Date.parse(entry.publish_at_utc)) throw new Error('YouTube did not confirm the exact private native schedule');
  if (video.status.rejectionReason || video.status.failureReason || video.processingDetails?.processingStatus === 'failed') throw new Error('YouTube processing failed');
  const metadata = { title: video.snippet.title, language: video.snippet.defaultLanguage, audio_language: video.snippet.defaultAudioLanguage, tags: video.snippet.tags };
  // The API returns tags alphabetically, independently of the upload order.
  const matches = metadata.title === entry.meta.youtube_title && metadata.language === entry.language && metadata.audio_language === entry.language && JSON.stringify([...(metadata.tags || [])].sort()) === JSON.stringify([...entry.meta.youtube_tags].sort());
  return { metadata, ready: matches && video.processingDetails?.processingStatus === 'succeeded' && video.status.uploadStatus === 'processed' };
}
