(() => {

const key='opl-subsite-drafts-v1';let drafts=[];const $=id=>document.getElementById(id);
function clean(v){if(!v||typeof v.name!=='string'||!v.name.trim()||v.name.length>80||/[\u0000-\u001f<>@]/.test(v.name))throw new Error('请填写非敏感节点名称');const u=new URL(v.url);if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||!u.hostname.includes('.')||/^[0-9.:[\]]+$/.test(u.hostname)||/\.(localhost|local|internal)$/.test(u.hostname))throw new Error('只填写无凭据、无查询参数的 HTTPS 域名地址');return {name:v.name.trim(),url:u.href,authDeclaration:['login','mfa'].includes(v.authDeclaration)?v.authDeclaration:'unverified',registration:'draft-local-only',mfaVerified:false,peerAcknowledged:false};}
function render(){const safe=[];for(const v of drafts.slice(0,32)){try{safe.push(clean(v))}catch{}}drafts=safe;$('preview').textContent=JSON.stringify(drafts,null,2);$('links').replaceChildren();for(const d of drafts){const p=document.createElement('p'),a=document.createElement('a');a.href=d.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=d.name+' ↗（提案，待复核）';p.append(a);$('links').append(p);}}
try{const v=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(v))drafts=v;render()}catch{drafts=[];render()}
$('proposal').onsubmit=e=>{e.preventDefault();try{const d=clean({name:$('name').value,url:$('url').value,authDeclaration:$('auth').value});if(drafts.length>=32)throw new Error('本地提案上限 32 项');drafts= drafts.filter(x=>x.url!==d.url).concat(d);render();localStorage.setItem(key,JSON.stringify(drafts));$('result').textContent='已暂存到当前浏览器，未登记或云同步。'}catch(e){$('result').textContent=e.message}};
$('download').onclick=()=>{const blob=new Blob([JSON.stringify({kind:'subsite-draft-checklist',registration:'not-submitted',nodes:drafts},null,2)],{type:'application/json'}),u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='subsite-drafts.json';a.click();URL.revokeObjectURL(u)};

})();
