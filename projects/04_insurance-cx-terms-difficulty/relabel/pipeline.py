import pandas as pd, numpy as np, openpyxl
U='/root/.claude/uploads/6f2fa44f-4c37-59bc-8577-4ae126e2027b/'
R='/mnt/user-data/outputs/insurance-cx/relabel/'
hb=pd.read_pickle('/tmp/claude-0/hb.pkl'); ga=pd.read_csv('/tmp/claude-0/gold3.csv',dtype=str)
gold={}
for _,r in ga.iterrows(): gold[(r.key,'issue_type')]=r.h_it; gold[(r.key,'ambiguity')]=str(r.h_am)
for _,r in hb.iterrows(): gold[(r.key,'issue_type')]=r.it; gold[(r.key,'ambiguity')]=str(r.am)
ans={}
for f,who in [('3eb1f2e1-1793774281195_human_sheet______.xlsx','팀원C'),('2044e484-1793774281196_human_sheet______.xlsx','팀원B')]:
    ws=openpyxl.load_workbook(U+f,data_only=True)['확인']
    for r in ws.iter_rows(min_row=5,values_only=True):
        if r[0]: ans[r[0]]=r[3]
mp={'언급 없음':'0','모호 인정':'1','명백하다고 판단':'2'}
v2=pd.read_csv(R+'판정_v2.csv',encoding='utf-8-sig',dtype=str)
asg=pd.read_csv(R+'사람확인_배정.csv',encoding='utf-8-sig',dtype=str)
hk=set(zip(asg.case_key,asg.label))
rows=[]
for _,r in v2.iterrows():
    k=(r.case_key,r.label); g=gold.get(k)
    auto=r.auto=='True'
    if k in hk:
        a=[ans[s] for s in r.ids.split(',')]
        if r.label=='ambiguity':
            a=[mp[x] for x in a]; h='1' if '1' in a else ('2' if '2' in a else '0')
        else: h=a[0]
        final=h; src='사람(조각)'
    else:
        h=None; final=r.llm1; src='자동'
    rows.append(dict(case_key=r.case_key,set=r.set,label=r.label,rule=r.rule,llm1=r.llm1,auto=auto,checked=k in hk,
                     human_snip=h,final=final,src=src,gold=g,final_ok=(final==g) if g is not None else None,
                     auto_ok=(r.llm1==g) if auto else None))
p=pd.DataFrame(rows); p.to_csv(R+'결과_파이프라인_최종.csv',index=False,encoding='utf-8-sig')
print(p.groupby(['set','label']).agg(n=('final_ok','size'),final_ok=('final_ok','sum')))
# 자동확정(세 판정 일치) 중 틀린 것
a=p[p.auto]
print('auto n',len(a),'auto wrong',(a.auto_ok==False).sum())
print(a[a.auto_ok==False][['case_key','set','label','rule','llm1','checked','human_snip','gold']].to_string())
# 사람 조각 확인의 정확도
c=p[p.checked]
print('checked',len(c),'human snip == gold',(c.human_snip==c.gold).sum())
print(c[['case_key','set','label','rule','llm1','auto','human_snip','gold']].to_string())
# 판정 없는 라벨(조각이 없어 v2에 없는 amb): set A 30-17=13, B 22-16=6 -> 규칙 0 그대로

# 전체 사건 기준(조각 없는 amb = 0)
allk=[(k,'A') for k in ga.key]+[(k,'B') for k in hb.key]
res=[]
for k,s in allk:
    for lab in ['issue_type','ambiguity']:
        q=p[(p.case_key==k)&(p.label==lab)]
        if len(q): f=q.final.iloc[0]; src=q.src.iloc[0]
        else: f='0'; src='조각 없음(0)'
        g=gold[(k,lab)]
        res.append(dict(case_key=k,set=s,label=lab,final=f,src=src,gold=g,ok=f==g))
r2=pd.DataFrame(res); r2.to_csv(R+'결과_파이프라인_전체사건.csv',index=False,encoding='utf-8-sig')
print(r2.groupby(['set','label']).ok.agg(['sum','size']))
print(r2[~r2.ok].to_string())
from sklearn.metrics import cohen_kappa_score as ck
for (s,l),d in r2.groupby(['set','label']): print(s,l,round(ck(d.gold.astype(str),d.final.astype(str)),2))
