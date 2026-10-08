"use strict";
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const zlib = require("node:zlib");
const {createHistoryTransfer} = require("../history-transfer");

// Scripted external backend/Worker HTTP boundaries; the module's filesystem,
// gzip, native crypto, fetch and orchestration execute without replacement.
async function environment(t) {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "wardly-transfer-test-"));
  const file = path.join(folder, "history.json.gz");
  const state = {backup:{format:"wardly-backup",version:1,counts:{matches:4},tables:{matches:[],meta:[]}}, puts:0, collisions:0, records:new Map(), imported:[], claims:0, deletes:0, backendError:null};
  const server = http.createServer(async (req,res) => {
    const chunks=[]; for await (const chunk of req) chunks.push(chunk);
    const body=Buffer.concat(chunks);
    const json=(status,data)=>{res.writeHead(status,{"content-type":"application/json"});res.end(JSON.stringify(data));};
    if(req.url === "/player/backup") {
      if(state.backendError) return json(503,{code:state.backendError,detail:"backend unavailable"});
      if(req.method === "GET") return json(200,state.backup);
      state.imported.push(JSON.parse(body)); return json(200,{added:4,linked:true});
    }
    const [,id,claim] = req.url.match(/^\/v1\/transfer\/([^/]+)(\/claim)?$/) || [];
    if(!id) return json(404,{code:"missing"});
    if(req.method === "PUT") {
      state.puts++; if(state.puts <= state.collisions) return json(409,{code:"taken"});
      assert.equal(req.headers["x-install-id"],"test-install");
      state.records.set(id,body);return json(201,{expires_at:1234});
    }
    if(claim) {
      state.claims++; if(!state.records.has(id)) return json(404,{code:"expired"});
      res.writeHead(200,{"content-type":"application/octet-stream"});return res.end(state.records.get(id));
    }
    if(req.method === "DELETE") { state.deletes++; state.records.delete(id); return json(200,{ok:true}); }
    return json(400,{code:"bad_method"});
  });
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  t.after(async()=>{ server.closeAllConnections(); await new Promise(resolve=>server.close(resolve));fs.rmSync(folder,{recursive:true,force:true}); });
  const requestBackendJson=async(route,method="GET",data)=>{
    const response=await fetch(base+route,{method,headers:{"content-type":"application/json"},body:data===undefined?undefined:JSON.stringify(data)});
    const payload=await response.json();
    if(!response.ok) {const error=new Error("backend unavailable");error.payload=payload;throw error;}
    return payload;
  };
  const ports={getWindow:()=>({isDestroyed:()=>false}),dialog:{showSaveDialog:async()=>({filePath:file}),showOpenDialog:async()=>({filePaths:[file]})},reportFolder:()=>folder,requestBackendJson,appendLog:()=>{},showItemInFolder:()=>{},backendRunning:()=>true,fetch,apiUrl:()=>base,installId:()=>"test-install"};
  return {state,file,ports,service:createHistoryTransfer(ports)};
}

test("file export/import executes genuine gzip/filesystem and backend HTTP",async t=>{
  const {state,file,service}=await environment(t);
  const saved=await service.exportHistory();
  assert.equal(saved.ok,true);assert.equal(saved.matches,4);
  assert.deepEqual(JSON.parse(zlib.gunzipSync(fs.readFileSync(file))),state.backup);
  assert.deepEqual(await service.importHistory(),{ok:true,added:4,linked:true});
  assert.deepEqual(state.imported,[state.backup]);
});
test("plain JSON import and damaged gzip preserve explicit outcomes",async t=>{
  const {state,file,service}=await environment(t);
  fs.writeFileSync(file,JSON.stringify(state.backup));assert.equal((await service.importHistory()).ok,true);
  fs.writeFileSync(file,Buffer.from([0x1f,0x8b,0x00]));assert.equal((await service.importHistory()).code,"not_backup");
  assert.equal(state.imported.length,1);
});
test("cancel, destroyed window and backend errors remain separate",async t=>{
  const {state,ports}=await environment(t);
  const canceled=createHistoryTransfer({...ports,dialog:{showSaveDialog:async()=>({canceled:true}),showOpenDialog:async()=>({canceled:true})}});
  assert.deepEqual(await canceled.exportHistory(),{ok:false,canceled:true});assert.deepEqual(await canceled.importHistory(),{ok:false,canceled:true});
  assert.deepEqual(await createHistoryTransfer({...ports,getWindow:()=>null}).exportHistory(),{ok:false,code:"no_window"});
  state.backendError="restore_failed";
  assert.equal((await createHistoryTransfer(ports).exportHistory()).code,"restore_failed");
});
test("code transfer encrypts over HTTP, retries collisions, imports and deletes",async t=>{
  const {state,service}=await environment(t);state.collisions=2;
  const sent=await service.sendHistoryByCode();assert.equal(sent.ok,true);assert.equal(state.puts,3);assert.equal(sent.expiresAt,1234);
  const encrypted=[...state.records.values()][0];assert.equal(encrypted.includes(Buffer.from("wardly-backup")),false);
  assert.deepEqual(await service.receiveHistoryByCode(sent.code),{ok:true,added:4,linked:true});assert.deepEqual(state.imported,[state.backup]);
  const deadline=Date.now()+1000;while(!state.deletes && Date.now()<deadline) await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(state.deletes,1);assert.equal(state.records.size,0);
});
test("collision attempt cap and oversized transfer do not publish",async t=>{
  const {state,service}=await environment(t);state.collisions=3;
  assert.deepEqual(await service.sendHistoryByCode(),{ok:false,code:"taken"});assert.equal(state.puts,3);
  state.backup.large=crypto.randomBytes(2_000_000).toString("base64");
  assert.deepEqual(await service.sendHistoryByCode(),{ok:false,code:"too_big"});assert.equal(state.puts,3);
});
test("bad and expired codes do not import",async t=>{
  const {state,service}=await environment(t);
  assert.deepEqual(await service.receiveHistoryByCode("bad"),{ok:false,code:"bad_code"});assert.equal(state.claims,0);
  const sent=await service.sendHistoryByCode();state.records.clear();
  assert.deepEqual(await service.receiveHistoryByCode(sent.code),{ok:false,code:"expired"});assert.equal(state.imported.length,0);
});
test("plain JSON export and failed restore retain local data and code",async t=>{
  const {state,file,ports}=await environment(t);
  const plain=file.replace(/\.gz$/,"");
  const service=createHistoryTransfer({...ports,dialog:{showSaveDialog:async()=>({filePath:plain}),showOpenDialog:async()=>({filePaths:[plain]})}});
  assert.equal((await service.exportHistory()).ok,true);
  assert.deepEqual(JSON.parse(fs.readFileSync(plain,"utf8")),state.backup);
  state.backendError="restore_failed";
  assert.equal((await service.importHistory()).code,"restore_failed");assert.equal(state.imported.length,0);
});
