"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const {create} = require("../renderer/app-texts");
const whatsNew = require("../renderer/whats-new");
test("control-panel catalogs retain functional copy and current patch history",()=>{
  const texts=create(whatsNew);
  assert.equal(texts.en.status.inGameTitle("Luna","10:00"),"In game: Luna, 10:00");
  assert.equal(texts.uk.backupLoaded(0,false),"Завантажено нових матчів: 0. Нічого не перезаписано.");
  assert.deepEqual(texts.en.whatsNew,whatsNew.texts("en"));assert.deepEqual(texts.uk.whatsNew,whatsNew.texts("uk"));
});
test("nested catalogs and update tables belong to each panel instance",()=>{
  const first=create(whatsNew),second=create(whatsNew);
  first.en.status.loadingTitle="changed";first.en.whatsNew["0.53.39"][0]="changed";
  assert.notEqual(first.en.status.loadingTitle,second.en.status.loadingTitle);
  assert.notEqual(first.en.whatsNew["0.53.39"][0],second.en.whatsNew["0.53.39"][0]);
});
