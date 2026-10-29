export async function api<T=any>(path:string,body?:unknown,method?:string):Promise<T>{
 const r=await fetch('/api'+path,{credentials:'include',method:method||(body?'POST':'GET'),headers:{'Content-Type':'application/json','X-Requested-With':'Hillwatch'},body:body?JSON.stringify(body):undefined});
 const data=await r.json();if(!r.ok)throw new Error(data.message||JSON.stringify(data.detail)||'Request failed');return data;
}
export type Route={id:string;description:string;distance_m:number;duration:string;geometry:any;corridor:any;segments:any[];origin:string;destination:string;corridor_m:number};
export type Incident={id:string;kind:string;latitude:number;longitude:number;observed_at:string;submitted_at:string;description:string;moderation:string;status:string;stale:boolean;duplicate_of?:string;flags:number;has_photo:boolean};
export const time=(value?:string)=>value?new Date(value).toLocaleString():'Not available';
const queueKey='hillwatch-incident-queue-v1';
export function queued():any[]{try{return JSON.parse(localStorage.getItem(queueKey)||'[]')}catch{return []}}
export function enqueue(body:unknown){const q=queued();q.push(body);localStorage.setItem(queueKey,JSON.stringify(q));}
export async function flushQueue(){const q=queued();while(q.length){await api('/incidents',q[0]);q.shift();localStorage.setItem(queueKey,JSON.stringify(q));}return q.length;}
