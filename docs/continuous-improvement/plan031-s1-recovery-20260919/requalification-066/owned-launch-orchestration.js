// Codex functions.exec orchestration used for the recorded owned launches.
(async function(kind,n){
const base="/home/auss/git_repos/samaust/Experiments_4DGS",dir="docs/continuous-improvement/plan031-s1-recovery-20260919/requalification-066",run="docs/resolve-blocker/plan031-progress-20260922",suffix=kind+"-"+String(n).padStart(3,"0");
async function event(i,role,tool,args){
const started={utc:new Date().toISOString()},result=await tools[tool](args);
let e={schema:"plan049-session-tool-event/v2",kind,index:n,ordinal:i,role,tool,arguments:args,result,started,returned:{utc:new Date().toISOString()}};
await tools.apply_patch("*** Begin Patch\n*** Add File: "+dir+"/owned-"+suffix+"-event-"+i+".json\n+"+JSON.stringify(e,null,2).split("\n").join("\n+")+"\n*** End Patch");
const r=await tools.exec_command({cmd:".local/envs/stg-colmap/bin/python -B - <<'PY'\nimport json,hashlib\nfrom pathlib import Path\np=Path('"+dir+"/owned-"+suffix+"-event-"+i+".json');e=json.loads(p.read_text());e['output_sha256']=hashlib.sha256(e['result']['output'].encode()).hexdigest()\nwith Path('"+run+"/main-session-049-"+suffix+"-event-00"+i+".json').open('x') as f:json.dump(e,f,indent=2);f.write('\\n')\nprint(json.dumps(e))\nPY",max_output_tokens:8000});
if(r.exit_code!==0)throw Error(r.output);return JSON.parse(r.output);
}
const args={cmd:"exec "+base+"/.local/envs/stg-colmap/bin/python -B "+base+"/"+run+"/launch-049-exec.py "+kind+" "+n+" 'Plan066 sampler source requalification under Codex'",shell:"/bin/bash",login:false,workdir:base,tty:true,sandbox_permissions:"require_escalated",yield_time_ms:1000,justification:"Run the reviewed Plan049 CPU-only "+kind+" after the exact AF_UNIX datagram socket retry succeeded.",prefix_rule:["exec",base+"/.local/envs/stg-colmap/bin/python","-B",base+"/"+run+"/launch-049-exec.py"],max_output_tokens:3000};
const e=await event(0,"start","exec_command",args);const id=e.result.session_id;if(!id)throw Error(JSON.stringify(e.result));store("owned-"+suffix,id);text({session_id:id});
await event(1,"readiness","write_stdin",{session_id:id,chars:JSON.stringify({schema:"plan049-main-start-frame/v1",session_id:id,event:e})+"\n",yield_time_ms:1000,max_output_tokens:6000});
await event(2,"pre_admission","write_stdin",{session_id:id,chars:"",yield_time_ms:1000,max_output_tokens:3000});
await event(3,"at_admission","write_stdin",{session_id:id,chars:"",yield_time_ms:1000,max_output_tokens:3000});
const prepared=await tools.exec_command({cmd:".local/envs/stg-colmap/bin/python -B "+dir+"/prepare_codex_admission.py "+n+" "+kind,yield_time_ms:10000,max_output_tokens:1000});text(prepared);if(prepared.exit_code!==0)throw Error("Admission not prepared");
return id;
})
