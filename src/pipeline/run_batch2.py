import json, os
from pathlib import Path
import pandas as pd, numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import cross_val_predict
from sklearn.preprocessing import LabelEncoder

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["MULTIPROCESSING_START_METHOD"] = "fork"

import multiprocessing
try:
    multiprocessing.set_start_method('fork', force=True)
except:
    pass

BATCH = Path("/Users/gexuancheng/Desktop/research2/data_clean/h4r_batch")
OUT = Path("/Users/gexuancheng/Desktop/research2/data_clean/governance_results")
SC = ["Pressure","CO2 Weld Flow","Feed","Primary Weld Current","Wire Consumed","Secondary Weld Voltage"]

all_csvs = sorted(BATCH.glob("*.csv"))
jpgs = sorted(BATCH.glob("*.jpg"))
samples = []
for csv in all_csvs:
    name = csv.name
    label = None
    for tag in [("burnthrough","burnthrough"),("crater","crater_crack"),("lack_of_fusion","lack_of_fusion"),
                ("excessive","excessive"),("overlap","overlap"),("good","good")]:
        if tag[0] in name: label = tag[1]; break
    if not label: continue
    for jpg in jpgs:
        if csv.stem[:20] in jpg.stem:
            samples.append({"csv": str(csv), "jpg": str(jpg), "label": label}); break

print(f"样本: {len(samples)}")
for l in sorted(set(s["label"] for s in samples)):
    print(f"  {l}: {sum(1 for s in samples if s['label']==l)}")

for s in samples:
    df = pd.read_csv(s["csv"])
    c = pd.to_numeric(df.get("Primary Weld Current",pd.Series([0])),errors='coerce').fillna(0)
    v = pd.to_numeric(df.get("Secondary Weld Voltage",pd.Series([0])),errors='coerce').fillna(0)
    co2 = pd.to_numeric(df.get("CO2 Weld Flow",pd.Series([0])),errors='coerce').fillna(0)
    s["n"]=len(df); s["c_mean"]=float(c.mean()); s["c_std"]=float(c.std()); s["c_max"]=float(c.max())
    s["v_max"]=float(v.max()); s["v_std"]=float(v.std())
    s["l1"]=0
    for col in SC:
        if col not in df.columns: s["l1"]+=1
    if (c>10).any() and (co2[c>10]<=0).any(): s["l1"]+=1
    X = df[SC].apply(pd.to_numeric,errors='coerce').fillna(0).values
    iso = IsolationForest(contamination=0.1,random_state=42,n_jobs=1)
    s["anom"]=int((iso.fit(X).predict(X)==-1).sum())
    s["fact"]=False
    if s["label"]=="good" and s["c_std"]>50: s["fact"]=True
    elif s["label"]=="burnthrough" and s["c_max"]<200: s["fact"]=True
    elif s["label"]=="crater_crack" and s["c_std"]<40: s["fact"]=True
    s["l3"]=0
    if v.diff().abs().max()>20: s["l3"]+=1
    if len(c)>10 and c.iloc[-1]>50: s["l3"]+=1
    s["pass"]=(s["l1"]==0) and (not s["fact"]) and (s["l3"]==0)

# Cleanlab
feats=[[s["c_mean"],s["c_std"],s["c_max"],s["v_max"],s["v_std"],s["anom"]] for s in samples]
X=np.array(feats); le=LabelEncoder(); y=le.fit_transform([s["label"] for s in samples])
cl_msg="未运行"
if len(set(y))>1 and len(y)>=10:
    cv=min(3,len(y)//2)
    if cv>=2:
        pp=cross_val_predict(RandomForestClassifier(50,random_state=42),X,y,cv=cv,method='predict_proba')
        from cleanlab.filter import find_label_issues
        from cleanlab.rank import get_label_quality_scores
        iss=find_label_issues(y,pp,return_indices_ranked_by="self_confidence")
        sc=get_label_quality_scores(y,pp)
        cl_msg=f"{len(iss)}个问题,均分={sc.mean():.3f}"
        for i,s in enumerate(samples):
            s["cl_score"]=float(sc[i]); s["cl_flag"]=i in iss
        print(f"Cleanlab: {cl_msg}")
        for idx in iss[:5]:
            print(f"  #{idx} {le.inverse_transform([y[idx]])[0]} 分数={sc[idx]:.3f}")

gp=sum(1 for s in samples if s["pass"])
print(f"\n结果: {len(samples)}样本, 通过{gp}, 复核{len(samples)-gp}")
for l in sorted(set(s["label"] for s in samples)):
    sub=[s for s in samples if s["label"]==l]
    print(f"  {l:20s}: {len(sub)}个(通过{sum(1 for s in sub if s['pass'])})")

r={"total":len(samples),"pass":gp,"review":len(samples)-gp,"cleanlab":cl_msg,
   "samples":[{"label":s["label"],"file":Path(s["csv"]).name[:30],"l1":s["l1"]==0,
               "fact":s["fact"],"l3":s["l3"]==0,"pass":s["pass"],
               "c_std":round(s["c_std"],1),"anom":s["anom"],
               "cl":round(s.get("cl_score",0),3)} for s in samples]}
with open(OUT/"batch_final.json","w") as f: json.dump(r,f,indent=2,ensure_ascii=False,default=str)
print(f"已保存")
