import { useEffect, useState } from "react";
const API = (import.meta as any).env.VITE_API_URL || "http://localhost:8080";
type Finding={code:string;message?:string;explanation?:string;severity?:string};
type History={id:number;type:string;created_at:string;summary:Record<string,unknown>};
export default function App(){
 const [report,setReport]=useState<any>(null),[history,setHistory]=useState<History[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(""),[mode,setMode]=useState("rules");
 async function call(path:string,body?:unknown){const res=await fetch(API+path,{method:body?"POST":"GET",headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});const data=await res.json();if(!res.ok)throw new Error(data.detail||res.statusText);return data;}
 async function refresh(){try{const h=await call("/api/patent-history?limit=20");setHistory(h.items||[]);}catch(e){setError(String(e));}}
 async function run(kind:string){setBusy(true);setError("");setMode(kind);try{const data=kind==="experiment"?await call("/api/patent-experiments",{include_llm:false}):await call("/api/patent-evaluate");setReport(data);await refresh();}catch(e){setError(String(e));}finally{setBusy(false);}}
 useEffect(()=>{refresh()},[]);
 const metrics=report?.baselines?.deterministic_rules||report||{};
 return <main><header><div><span className="eyebrow">AGENTCANVAS / RESEARCH CONSOLE</span><h1>Patent output evaluation</h1><p>Deterministic checks, semantic proxies and reproducible experiments.</p></div><span className="tag">Prototype · v0.2</span></header>
 <section className="actions"><button disabled={busy} onClick={()=>run("rules")}>{busy&&mode==="rules"?"Running…":"Run deterministic benchmark"}</button><button className="secondary" disabled={busy} onClick={()=>run("experiment")}>{busy&&mode==="experiment"?"Running…":"Run baseline comparison"}</button><a href="http://localhost:8080/docs" target="_blank" rel="noreferrer">API docs ↗</a></section>
 {error&&<p className="error">{error}</p>}
 {report&&<><section className="metrics"><article><small>Cases</small><strong>{report.case_count??report.dataset_size}</strong></article><article><small>Precision</small><strong>{Math.round((metrics.precision??0)*100)}%</strong></article><article><small>Recall</small><strong>{Math.round((metrics.recall??0)*100)}%</strong></article><article><small>F1</small><strong>{Math.round((metrics.f1??0)*100)}%</strong></article></section>
 {report.results&&<section><h2>Case-level findings</h2><div className="cards">{report.results.map((r:any)=><article className="case" key={r.id}><div className="casehead"><b>{r.id} · {r.title}</b><span>{r.matched_expected_failures?"Expected label found":"Review"}</span></div><p>{r.category}</p><p className="muted">{r.candidate_output}</p>{r.findings.map((f:Finding,i:number)=><p className="finding" key={i}><b>{f.code}</b> — {f.message}</p>)}</article>)}</div></section>}
 {report.baselines&&<section><h2>Baseline comparison</h2><div className="cards">{Object.entries(report.baselines).map(([name,m]:any)=><article className="case" key={name}><b>{name.replaceAll("_"," ")}</b><p>Precision {m.precision} · Recall {m.recall} · F1 {m.f1}</p><p className="muted">TP {m.true_positives} / FP {m.false_positives} / FN {m.false_negatives}</p></article>)}</div></section>}</>}
 <section><h2>Evaluation history</h2><div className="history">{history.map(item=><article key={item.id}><b>#{item.id} · {item.type}</b><span>{new Date(item.created_at).toLocaleString()}</span></article>)}{!history.length&&<p className="muted">No saved evaluations yet. Run a benchmark to create history.</p>}</div></section>
 <footer>Research prototype only. Synthetic fixture scores are not real-world patent QA accuracy or legal advice.</footer></main>
}