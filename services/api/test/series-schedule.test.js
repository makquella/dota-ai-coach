import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scheduledVideoState } from '../../../scripts/promo/series_schedule_verify.mjs';

test('native verification waits for processing and delayed metadata before accepting the schedule', () => {
  const entry = { language: 'uk', publish_at_utc: '2026-10-17T14:00:00Z', meta: { youtube_title: 'Wardly review', youtube_tags: ['Wardly', 'Dota 2'] } };
  const video = {
    snippet: { channelId: 'wardly', title: entry.meta.youtube_title, defaultLanguage: 'uk', defaultAudioLanguage: 'uk' },
    status: { privacyStatus: 'private', publishAt: entry.publish_at_utc, uploadStatus: 'uploaded' },
    processingDetails: { processingStatus: 'processing' }
  };
  assert.equal(scheduledVideoState(video, entry, 'wardly').ready, false);
  video.status.uploadStatus = 'processed';
  video.processingDetails.processingStatus = 'succeeded';
  assert.equal(scheduledVideoState(video, entry, 'wardly').ready, false);
  video.snippet.tags = ['Dota 2', 'Wardly'];
  assert.equal(scheduledVideoState(video, entry, 'wardly').ready, true);
  video.snippet.defaultAudioLanguage = 'en';
  assert.equal(scheduledVideoState(video, entry, 'wardly').ready, false);
  video.status.publishAt = '2026-10-17T15:00:00Z';
  assert.throws(() => scheduledVideoState(video, entry, 'wardly'), /exact private native schedule/);
});
