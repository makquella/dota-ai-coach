"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const {valid} = require("../renderer/finding-evidence");
const base = {field:"obs_placed", source:"opendota.obs_log", precision:"log_count", value:0, observed_at:null, coverage:null};

test("parsed counts preserve known zero and reject malformed metadata", () => {
  assert.equal(valid(base), true);
  for (const value of [true, "0", -1, 1.5, NaN, Infinity, Number.MAX_SAFE_INTEGER+1]) assert.equal(valid({...base,value}),false);
  for (const patch of [{field:"__proto__"},{field:["obs_placed"]},{source:"__proto__"},{source:"unknown"},{observed_at:0},{precision:"sample"},{coverage:undefined}]) assert.equal(valid({...base,...patch}),false);
});
test("GSI estimates require explicit valid recording coverage", () => {
  const coverage = {start:0,end:600,gaps:[],complete:true};
  const row = {...base,source:"gsi.inventory_changes",precision:"inventory_estimate",coverage};
  assert.equal(valid(row),true);
  assert.equal(valid({...row,coverage:null}),false);
  for (const patch of [{start:20},{start:true},{end:-1},{gaps:[[30,60]]},{gaps:[[0,700]],complete:false},{gaps:"none"}]) assert.equal(valid({...row,coverage:{...coverage,...patch}}),false);
  assert.equal(valid({...row,coverage:{...coverage,gaps:[[30,60]],complete:false}}),true);
});
test("LH sample timestamp and early-death source stay field specific", () => {
  const row = {...base,field:"lh10",source:"opendota.lh_t",precision:"sample",observed_at:600};
  assert.equal(valid(row),true);
  assert.equal(valid({...row,observed_at:585}),false);
  assert.equal(valid({...row,source:"opendota.kills_log"}),false);
  assert.equal(valid({...base,field:"lane_deaths",source:"opendota.kills_log"}),true);
  assert.equal(valid({...base,field:"lane_deaths",source:"opendota.obs_log"}),false);
});
