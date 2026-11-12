import numpy as np
from ..constants.enums import PHASES

MIN_STATION_ROWS=8

def attribute(matrix,replicates=200,seed=42,tail_quantile=.95,resample_scope="pooled",stations=None,required_stations=None):
 rng=np.random.default_rng(seed);n,k=matrix.shape
 if n<8 or k!=4 or not np.isfinite(matrix).all() or (matrix<0).any(): raise ValueError("非法阶段时延矩阵")
 if resample_scope=="pooled": return _pooled(matrix,rng,replicates,seed,tail_quantile,_counts(stations,n))
 if resample_scope=="by_station": return _by_station(matrix,stations,rng,replicates,seed,tail_quantile,required_stations)
 raise ValueError(f"未知重采样方式：{resample_scope}")

def _counts(stations,n):
 if stations is None or len(stations)!=n: return None
 counts={}
 for s in stations: counts[str(s)]=counts.get(str(s),0)+1
 return dict(sorted(counts.items()))

def _pack(samples,tails,observed,medians,replicates,seed,tail_quantile):
 arr=np.array(samples);effects=arr.mean(axis=0);positive=np.maximum(effects,0);den=float(positive.sum())
 return {"observed_tail":observed,"modeled_tail":float(np.mean(tails)),"replicates":replicates,"seed":seed,"quantile":tail_quantile,"contributions":[{"phase":p,"reduction":float(effects[j]),"share":float(positive[j]/den) if den else 0.,"low":float(np.quantile(arr[:,j],.025)),"high":float(np.quantile(arr[:,j],.975)),"median":float(medians[j])} for j,p in enumerate(PHASES)]}

def _pooled(matrix,rng,replicates,seed,tail_quantile,station_counts):
 n,k=matrix.shape
 medians=np.median(matrix,axis=0);observed=float(np.quantile(matrix.sum(axis=1),tail_quantile))
 # Resample each phase independently; the modeled tail isolates phase dispersion, not route causality.
 samples=[];tails=[]
 for _ in range(replicates):
  synthetic=np.column_stack([rng.choice(matrix[:,j],size=n,replace=True) for j in range(k)])
  baseline=float(np.quantile(synthetic.sum(axis=1),tail_quantile));tails.append(baseline)
  effect=[]
  for j in range(k):
   replaced=synthetic.copy();replaced[:,j]=medians[j]
   effect.append(baseline-float(np.quantile(replaced.sum(axis=1),tail_quantile)))
  samples.append(effect)
 result=_pack(samples,tails,observed,medians,replicates,seed,tail_quantile)
 result["resample_scope"]="pooled"
 if station_counts: result["station_counts"]=station_counts
 result["assumption"]="阶段独立重采样；将某阶段置于其中位数后比较模拟总时延尾部分位。区间表示重采样波动，不是因果效应。"
 return result

def _by_station(matrix,stations,rng,replicates,seed,tail_quantile,required_stations):
 n,k=matrix.shape
 if stations is None or len(stations)!=n: raise ValueError("按站点重采样需要每票对应的站点标签")
 counts={}
 for s in stations: counts[str(s)]=counts.get(str(s),0)+1
 for s in required_stations or []: counts.setdefault(str(s),0)
 short=[f"{s}站仅{c}票" for s,c in sorted(counts.items()) if c<MIN_STATION_ROWS]
 if short: raise ValueError("按站点重采样要求每站至少8票完整观测，"+"、".join(short)+"；请改用跨站混合口径或调整线路范围")
 labels=sorted(counts)
 blocks=[(s,matrix[[i for i,x in enumerate(stations) if str(x)==s]]) for s in labels]
 medians={s:np.median(part,axis=0) for s,part in blocks}
 counts={s:int(part.shape[0]) for s,part in blocks}
 observed=float(np.quantile(matrix.sum(axis=1),tail_quantile))
 # Resample each phase independently within its own station, then merge with station
 # ticket counts preserved; the overall tail is the quantile of the merged sample,
 # never an average of per-station quantiles. Counterfactuals use the station median.
 samples=[];tails=[]
 for _ in range(replicates):
  parts=[np.column_stack([rng.choice(part[:,j],size=part.shape[0],replace=True) for j in range(k)]) for _,part in blocks]
  synthetic=np.vstack(parts)
  baseline=float(np.quantile(synthetic.sum(axis=1),tail_quantile));tails.append(baseline)
  effect=[]
  for j in range(k):
   replaced=synthetic.copy();start=0
   for s,part in blocks:
    stop=start+part.shape[0];replaced[start:stop,j]=medians[s][j];start=stop
   effect.append(baseline-float(np.quantile(replaced.sum(axis=1),tail_quantile)))
  samples.append(effect)
 result=_pack(samples,tails,observed,np.median(matrix,axis=0),replicates,seed,tail_quantile)
 result["resample_scope"]="by_station";result["station_counts"]=counts
 result["assumption"]="按站点分层重采样：各站保留自身票数，阶段仅在站内独立有放回抽取；反事实将该阶段固定为本站中位数后，对合并样本求整体尾分位，不对各站分位数取平均。区间表示重采样波动，不是因果效应。"
 return result
