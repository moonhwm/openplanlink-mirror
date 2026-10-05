"""Read-only, stdlib-only document preflight; output never includes body matches."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone,timedelta
import hashlib,io,json,re,sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile,BadZipFile

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
BJT=timezone(timedelta(hours=8))
LICENSES={
    'AGPL-3.0-only':'https://spdx.org/licenses/AGPL-3.0-only.html',
    'GPL-3.0-only':'https://spdx.org/licenses/GPL-3.0-only.html',
    'SSPL-1.0':'https://www.mongodb.com/legal/licensing/server-side-public-license',
    'CC-BY-SA-4.0':'https://spdx.org/licenses/CC-BY-SA-4.0.html',
    'ODbL-1.0':'https://spdx.org/licenses/ODbL-1.0.html',
}
CREDENTIALS=[(kind,re.compile(p,re.I)) for kind,p in (
    ('gateway_key',r'\bs'+r'k-[A-Za-z0-9_+/=-]{16,}'),
    ('cloud_access_key',r'\bAK'+r'IA[0-9A-Z]{16}\b|\bAKID[A-Za-z0-9]{13,40}\b'),
    ('sendkey',r'\bSCT\d+[A-Za-z0-9]{20,}\b'),
    ('bearer',r'\bBearer\s+[A-Za-z0-9_+/=.\-]{16,}'),
    ('url_password',r'://[^/\s:@]+:[^/\s@]+@'),
    ('private_key',r'-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRI'+r'VATE KEY-----'),
)]
NEGATED=re.compile(r'不是|并非|不属于|不得|不能|不提供|不构成|无法|≠|非开源|不等于')


def credential_issues(text,location):
    issues=[]
    for kind,pattern in CREDENTIALS:
        count=len(pattern.findall(text))
        if count:issues.append({'code':'credential_like_pattern','kind':kind,'location':location,'count':count})
    return issues


def review_units(units: list[str]) -> tuple[list[dict],list[dict]]:
    issues=[];license_locations={};terms=Counter()
    for number,item in enumerate(units,1):
        location,text=item if isinstance(item,tuple) else (f'unit:{number}',item)
        issues.extend(credential_issues(text,location))
        for word in ('幂等','等幂'):terms[word]+=text.count(word)
        for license_id in LICENSES:
            if re.search(r'(?<![A-Za-z0-9-])'+re.escape(license_id)+r'(?![A-Za-z0-9-])',text):
                license_locations.setdefault(license_id,[]).append(location)
        for sentence in re.split(r'[。！？\n]',text):
            rules=(
                ('sspl_open_source_claim',r'SSPL.{0,45}开源'),
                ('hmac_nonrepudiation_claim',r'HMAC.{0,60}(?:不可否认|数字签名)'),
                ('mac_as_auth_factor',r'MAC.{0,40}(?:第二因素|MFA)'),
                ('blanket_agpl_api_scope',r'AGPL.{0,70}(?:所有|全部|任何).{0,40}(?:API|后端)'),
                ('kimi_deployment_assertion',r'Kimi.{0,50}(?:已部署|部署完成|已上线)'),
                ('local_hook_absolute_gate',r'(?:GitHook|pre-commit|Git\s*hook).{0,60}(?:无法绕过|绝对阻断)'),
            )
            for code,pattern in rules:
                for match in re.finditer(pattern,sentence,re.I):
                    prefix=sentence[max(0,match.start()-12):match.start()]
                    if NEGATED.search(match.group()) or re.search(r'不得(?:把|将)?$|不能(?:把|将)?$',prefix):continue
                    if code=='kimi_deployment_assertion' and re.search(r'待核|冲突|原文|声称|宣称',match.group()+sentence[match.end():match.end()+12]):continue
                    issues.append({'code':code,'location':location,'disposition':'human_review'});break
        if 'AGPL' in text and 'SSPL' in text and re.search(r'叠加|附加|双重|同时适用',text):
            issues.append({'code':'license_combination_needs_rights_matrix','location':location,'disposition':'human_review'})
    if terms['幂等'] and terms['等幂']:
        issues.append({'code':'idempotency_terms_mixed','counts':dict(terms),'disposition':'define_glossary'})
    elif terms['等幂']:
        issues.append({'code':'idempotency_alias_needs_definition','counts':dict(terms),'disposition':'human_review'})
    licenses=[{'spdx_id':key,'mentioned_at':where,'primary_reference':LICENSES[key],
               'license_effect_or_compatibility_verified':False} for key,where in license_locations.items()]
    return issues,licenses


def outline_units(document):
    if not isinstance(document,dict) or not isinstance(document.get('data'),dict):raise ValueError('invalid_outline')
    data=document['data']
    if not isinstance(data.get('mainBody'),list) or not isinstance(data.get('title'),(str,list)):
        raise ValueError('invalid_outline')
    units=[];unknown=Counter()
    def inline(value):
        if isinstance(value,str):return value
        if isinstance(value,list):return ''.join(inline(x) for x in value)
        if isinstance(value,dict):
            if value.get('type')!='text':
                kind='inline_kind_sha256_'+hashlib.sha256(str(value.get('type')).encode('utf-8')).hexdigest()[:12]
                unknown[kind]+=1
                return ''
            if not isinstance(value.get('content'),str):
                unknown['invalid_inline_text_content']+=1
                return ''
            return value['content']
        unknown['invalid_inline_value']+=1
        return ''
    def walk(node,path):
        if not isinstance(node,dict):raise ValueError('invalid_outline_node')
        kind=node.get('type')
        if kind in ('heading','paragraph','tableCell','codeBlock'):
            text=inline(node.get('content'))
            if text:units.append((path,text))
        elif kind in ('table','tableRow','highlight','column','columnItem'):
            content=node.get('content') or []
            if not isinstance(content,list):raise ValueError('invalid_outline_children')
            for index,child in enumerate(content):walk(child,f'{path}.content[{index}]')
        else:unknown['kind_sha256_'+hashlib.sha256(str(kind).encode('utf-8')).hexdigest()[:12]]+=1
    title=inline(data['title'])
    if title:units.append(('data.title',title))
    for index,block in enumerate(data['mainBody']):walk(block,f'data.mainBody[{index}]')
    return units,dict(unknown)


def check_file(path: Path) -> dict:
    result={'path':str(path.resolve()),'read_at_bjt':datetime.now(BJT).isoformat(),
            'body_acquired':False,'issues':[],'formal_approval':False,
            'cloud_acl_or_history_verified':False,'native_wps_server_import_verified':False}
    try:
        before=path.stat();data=path.read_bytes();after=path.stat()
        result.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            stable_read=before.st_size==after.st_size==len(data) and before.st_mtime_ns==after.st_mtime_ns)
        units=[]
        if data.startswith(b'qonline\x00'):
            result.update(kind='wps_cloud_pointer',format_status='cloud_body_needed')
            result['issues'].append({'code':'cloud_pointer_is_not_body'})
        elif path.suffix.lower()=='.docx':
            with ZipFile(io.BytesIO(data)) as package:
                if package.testzip() is not None:raise BadZipFile('crc')
                names=package.namelist();document=ET.fromstring(package.read('word/document.xml'))
                units=[(f'docx:paragraph:{number}',''.join(n.text or '' for n in p.iter(W+'t')))
                       for number,p in enumerate(document.iter(W+'p'),1)]
                comments=ET.fromstring(package.read('word/comments.xml')) if 'word/comments.xml' in names else None
                result.update(kind='docx_ooxml',body_acquired=True,format_status='local_container_checked',
                    docx={'zip_crc':'pass','tracked_insertions':sum(1 for _ in document.iter(W+'ins')),
                          'tracked_deletions':sum(1 for _ in document.iter(W+'del')),
                          'comments':sum(1 for _ in comments.iter(W+'comment')) if comments is not None else 0,
                          'media':sum(n.startswith('word/media/') and not n.endswith('/') for n in names),
                          'embeddings':sum(n.startswith('word/embeddings/') and not n.endswith('/') for n in names)})
                # Comments and deleted text can also contain credential fragments.
                units.extend((f'docx:deleted_text:{number}',n.text or '') for number,n in enumerate(document.iter(W+'delText'),1))
                if comments is not None:
                    units.extend((f'docx:comment_paragraph:{number}',''.join(n.text or '' for n in p.iter(W+'t')))
                                 for number,p in enumerate(comments.iter(W+'p'),1))
                for index,name in enumerate(sorted(n for n in names if n.endswith('.rels')),1):
                    relationships=ET.fromstring(package.read(name))
                    for number,item in enumerate(relationships,1):
                        for attribute,value in enumerate(item.attrib.values(),1):
                            result['issues'].extend(credential_issues(value,f'docx:relationship_part:{index}:item:{number}:attribute:{attribute}'))
                if result['docx']['media'] or result['docx']['embeddings']:
                    result['issues'].append({'code':'binary_attachment_content_not_examined','media':result['docx']['media'],'embeddings':result['docx']['embeddings']})
        else:
            text=data.decode('utf-8-sig')
            if text.lstrip().startswith('{'):
                units,unknown=outline_units(json.loads(text))
                has_body=any(location.startswith('data.mainBody[') and value.strip() for location,value in units)
                result.update(kind='structured_otl_candidate',body_acquired=bool(has_body and not unknown),
                              format_status='structural_candidate_only',unknown_node_kinds=unknown)
                result['issues'].extend(credential_issues(text,'otl:serialized_data'))
                if unknown:result['issues'].append({'code':'unread_outline_nodes','node_counts':unknown})
                if not has_body:result['issues'].append({'code':'empty_or_unread_outline_body'})
            else:
                units=[(f'text:line:{number}',line) for number,line in enumerate(text.splitlines(),1)];result.update(kind='utf8_text',body_acquired=True,
                    format_status='text_outline_not_native_verified' if path.suffix.lower()=='.otl' else 'plain_text')
        if units:
            issues,licenses=review_units(units);result['issues'].extend(issues)
            result.update(examined_units=len(units),examined_text_characters=sum(len(u[1]) for u in units),license_mentions=licenses)
        if result.get('stable_read') is False:result['issues'].append({'code':'source_changed_during_read'})
    except (OSError,UnicodeError,BadZipFile,ET.ParseError,KeyError,ValueError,TypeError,RecursionError):
        result.update(kind='unreadable_or_unsupported',format_status='not_verified',body_acquired=False)
        result['issues'].append({'code':'read_or_structure_failed'})
    result['status']='review_needed' if result['issues'] or not result['body_acquired'] else 'local_preflight_clear'
    return result


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    report={'schema':'openplanlink.document-preflight/1','reports':[check_file(p) for p in args.input],
            'scope':'local_readonly_preflight; no legal/office approval or deployment assertion'}
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        with args.output.open('x',encoding='utf-8') as stream:stream.write(encoded+'\n')
    else:print(encoded)
    return 2 if any(r['kind']=='unreadable_or_unsupported' for r in report['reports']) else 0


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');raise SystemExit(main())
