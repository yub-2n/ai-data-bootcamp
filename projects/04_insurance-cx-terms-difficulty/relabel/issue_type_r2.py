import pandas as pd, re, sys
I='/mnt/user-data/uploads/insurance-cx/data/interim/'
cs=pd.read_csv(I+'cases.csv'); dec=pd.read_csv(I+'decisions.csv')
dec=dec.drop_duplicates('nttId')
KW_M=['보상하지않는','보상하지아니하는','지급하지않는','지급하지아니하는','면책']
KW_G=['알릴의무','고지','설명의무']
OPEN='(（【\\[〔<'; CLOSE=')）】\\]〕>'
pat=re.compile(r'(제\s*\d+\s*조(?:\s*의\s*\d+)?)\s*['+OPEN+r']([^'+CLOSE+r'\n]{1,40})['+CLOSE+r']')
LAW=re.compile(r'(법|시행령|시행세칙|규정|법률)[」』\s]*$')
def kw(s,kws): s=re.sub(r'\s','',s); return any(k in s for k in kws)
def typ(s):
    if kw(s,KW_M): return '면책'
    if kw(s,KW_G): return '고지·설명'
    return None
def r2(title,judg):
    t=typ(str(title))
    if t: return t,'안건명'
    titles=[]
    for m in pat.finditer(str(judg) if pd.notna(judg) else ''):
        pre=str(judg)[max(0,m.start()-12):m.start()]
        if LAW.search(pre): continue
        titles.append(m.group(2))
    if not titles: return '보상범위·정의','조제목없음'
    t=typ(titles[0])
    if t: return t,'첫 조 제목'
    if any(kw(x,KW_M) for x in titles[1:]): return '면책','뒤 조 제목(면책)'
    if any(kw(x,KW_G) for x in titles[1:]): return '고지·설명','뒤 조 제목(고지·설명)'
    return '보상범위·정의','기본값'
cs=cs.drop_duplicates('case_key').merge(dec[['nttId','위원회_판단','안건명']],on='nttId',how='left')
out=[]
for _,r in cs.iterrows():
    t,src=r2(r.title if pd.notna(r.title) else r.안건명, r.위원회_판단)
    out.append((r.case_key,t,src,r.issue_type,pd.isna(r.exclude_reason),pd.isna(r.위원회_판단)))
o=pd.DataFrame(out,columns=['case_key','issue_type_r2','r2_source','issue_type_r1','analysis','no_judg'])
o.to_csv('/tmp/claude-0/r2_all.csv',index=False,encoding='utf-8-sig')

# 구현 보충: R1이 보상범위·정의일 때만 뒤 조 제목 확인
def r2b(r):
    if r.issue_type_r1 in ('면책','고지·설명'): return r.issue_type_r1,'R1 그대로'
    if r.r2_source in ('뒤 조 제목(면책)','뒤 조 제목(고지·설명)'): return r.issue_type_r2,r.r2_source
    return '보상범위·정의','R1 그대로'
o[['issue_type_r2','r2_source']]=o.apply(lambda r: pd.Series(r2b(r)),axis=1)
o.to_csv('/tmp/claude-0/r2_all.csv',index=False,encoding='utf-8-sig')
