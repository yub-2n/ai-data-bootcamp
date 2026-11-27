import pandas as pd, numpy as np, openpyxl, json, sys
from sklearn.metrics import cohen_kappa_score
U='/root/.claude/uploads/6f2fa44f-4c37-59bc-8577-4ae126e2027b/'
R='/mnt/user-data/outputs/insurance-cx/relabel/'
OUT={}

def kap(a,b):
    a=[str(x) for x in a]; b=[str(x) for x in b]
    if len(set(a)|set(b))<2: return float('nan')
    return cohen_kappa_score(a,b)

# ---------- B set: 유빈 labels ----------
wb=openpyxl.load_workbook(U+'8a202068-1793774300060_____________________________________.xlsx',data_only=True)
ws=wb['결과표']; rows=list(ws.iter_rows(values_only=True))
hb=pd.DataFrame(rows[1:],columns=rows[0])[['번호','사건번호','본안 판단','cited','partial','issue_type','explained_duty','ambiguity','Q7-1 판례']]
hb.columns=['no','key','bon','cited','partial','it','ed','am','q71']
# C03: Q1 '아니오'지만 Q2 '예' + 지급하라 → 입력 실수로 보고 cited=1 로 둠(확인 요청)
hb.loc[hb.no=='C03','cited']='1'
hb.loc[hb.no=='C22','q71']='해당 없음'
for c in ['cited','partial','ed','am']: hb[c]=hb[c].astype(int)
ch=pd.read_csv('/mnt/user-data/outputs/insurance-cx/docs/챌린지셋_목록.csv',encoding='utf-8-sig')
hb=hb.merge(ch[['번호','빈틈유형']].rename(columns={'번호':'no','빈틈유형':'gap'}),on='no')

# 규칙(cases.csv)
cs=pd.read_csv('/mnt/user-data/uploads/insurance-cx/data/interim/cases.csv')
cs=cs.drop_duplicates('case_key')
m=cs.set_index('case_key')
def rv(k,c):
    v=m.loc[k,c] if k in m.index else np.nan
    return v
for c,cc in [('cited','m_cited'),('partial','m_partial'),('issue_type','m_it'),('explained_duty','m_ed'),('ambiguity','m_am')]:
    hb[cc]=[rv(k,c) for k in hb.key]
# LLM 전체 읽기
lb=pd.read_csv(R+'결과_전체읽기LLM/라벨_LLM_챌린지.csv',encoding='utf-8-sig',dtype=str)
lb=lb.rename(columns={'번호':'no','cited':'l_cited','partial':'l_partial','issue_type':'l_it','explained_duty':'l_ed','ambiguity':'l_am','확신도':'l_conf'})
hb=hb.merge(lb[['no','l_cited','l_partial','l_it','l_ed','l_am','l_conf']],on='no')
# 조각 LLM
v2=pd.read_csv(R+'판정_v2.csv',encoding='utf-8-sig',dtype=str)
vb=v2[v2.set=='B']
hb['v2_it']=[ (vb[(vb.case_key==k)&(vb.label=='issue_type')].llm1.tolist() or [np.nan])[0] for k in hb.key]
hb['v2_am']=[ (vb[(vb.case_key==k)&(vb.label=='ambiguity')].llm1.tolist() or ['0(조각없음)'])[0] for k in hb.key]
hb['v2_am_n']=hb.v2_am.replace({'0(조각없음)':'0'})
for c in ['m_cited','m_partial','m_ed','m_am']:
    hb[c]=pd.to_numeric(hb[c],errors='coerce').astype('Int64')
for c in ['l_cited','l_partial','l_ed','l_am']: hb[c]=hb[c].astype(int)
hb.to_csv(R+'결과_B셋_비교표.csv',index=False,encoding='utf-8-sig')

# A set
ga=pd.read_csv('/tmp/claude-0/gold3.csv',dtype=str)

def table(df,pairs):
    out=[]
    for lab,h,cols in pairs:
        for name,c in cols:
            if c not in df: continue
            a=df[h].astype(str); b=df[c].astype(str).str.replace('.0','',regex=False)
            ok=(a==b).sum()
            out.append(dict(label=lab,method=name,agree=int(ok),n=len(df),kappa=round(kap(a,b),2)))
    return pd.DataFrame(out)
pairsA=[('cited','h_cited',[('규칙','m_cited'),('LLM 전체','l_cited')]),
        ('partial','h_partial',[('규칙','m_partial'),('LLM 전체','l_partial')]),
        ('issue_type','h_it',[('규칙','m_it'),('LLM 전체','l_it'),('LLM 조각','v2_it')]),
        ('explained_duty','h_ed',[('규칙','m_ed'),('LLM 전체','l_ed')]),
        ('ambiguity','h_am',[('규칙','m_am'),('LLM 전체','l_am'),('LLM 조각','v2_am')])]
pairsB=[('cited','cited',[('규칙','m_cited'),('LLM 전체','l_cited')]),
        ('partial','partial',[('규칙','m_partial'),('LLM 전체','l_partial')]),
        ('issue_type','it',[('규칙','m_it'),('LLM 전체','l_it'),('LLM 조각','v2_it')]),
        ('explained_duty','ed',[('규칙','m_ed'),('LLM 전체','l_ed')]),
        ('ambiguity','am',[('규칙','m_am'),('LLM 전체','l_am'),('LLM 조각','v2_am_n')])]
tA=table(ga,pairsA); tB=table(hb,pairsB)
tA.to_csv(R+'결과_A셋_일치.csv',index=False,encoding='utf-8-sig')
tB.to_csv(R+'결과_B셋_일치.csv',index=False,encoding='utf-8-sig')
print(tA.to_string()); print(tB.to_string())

# 빈틈 유형별: 각 유형의 '해당 라벨'
focus={'G1':('am','m_am','l_am','v2_am_n'),'G4':('am','m_am','l_am','v2_am_n'),
       'G2':('it','m_it','l_it','v2_it'),'G5':('it','m_it','l_it','v2_it'),'G3':('ed','m_ed','l_ed',None)}
rows=[]
for g,(h,mm,ll,vv) in focus.items():
    d=hb[hb.gap==g]
    r=dict(gap=g,label={'am':'ambiguity','it':'issue_type','ed':'explained_duty'}[h],n=len(d),
           규칙=int((d[h].astype(str)==d[mm].astype(str)).sum()),
           LLM전체=int((d[h].astype(str)==d[ll].astype(str)).sum()))
    r['LLM조각']=int((d[h].astype(str)==d[vv].astype(str)).sum()) if vv else None
    rows.append(r)
gt=pd.DataFrame(rows); gt.to_csv(R+'결과_B셋_빈틈유형별.csv',index=False,encoding='utf-8-sig'); print(gt)

# 2x2 / crosstab
def ct(df,h,c): return pd.crosstab(df[h].astype(str),df[c].astype(str).str.replace('.0','',regex=False),rownames=['사람'],colnames=[c])
OUT['ctA_am_m']=ct(ga,'h_am','m_am'); OUT['ctA_am_l']=ct(ga,'h_am','l_am'); OUT['ctA_am_v']=ct(ga,'h_am','v2_am')
OUT['ctA_it_m']=ct(ga,'h_it','m_it'); OUT['ctA_it_l']=ct(ga,'h_it','l_it')
OUT['ctB_am_m']=ct(hb,'am','m_am'); OUT['ctB_am_l']=ct(hb,'am','l_am'); OUT['ctB_am_v']=ct(hb,'am','v2_am_n')
OUT['ctB_it_m']=ct(hb,'it','m_it'); OUT['ctB_it_l']=ct(hb,'it','l_it'); OUT['ctB_it_v']=ct(hb,'it','v2_it')
OUT['ctB_ed_m']=ct(hb,'ed','m_ed'); OUT['ctB_ed_l']=ct(hb,'ed','l_ed')
OUT['ctB_cited_l']=ct(hb,'cited','l_cited'); OUT['ctB_partial_l']=ct(hb,'partial','l_partial'); OUT['ctB_partial_m']=ct(hb,'partial','m_partial')
for k,v in OUT.items(): print(k); print(v)

# Q7-1
q=hb[hb.am==1].copy()
q['규칙1']=(q.m_am.astype(str)=='1'); q['LLM전체1']=(q.l_am==1); q['LLM조각1']=(q.v2_am_n=='1')
print(q[['no','key','gap','q71','m_am','l_am','v2_am']].to_string())
print(q.groupby('q71')[['규칙1','LLM전체1','LLM조각1']].agg(['sum','count']))
hb.to_pickle('/tmp/claude-0/hb.pkl')
