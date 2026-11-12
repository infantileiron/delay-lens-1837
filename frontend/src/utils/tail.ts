// 尾部归因结果核对工具：新旧快照均可使用。旧结果缺少resample_scope/station_counts时
// 回退为跨站混合口径，并从结果行推导站点票数，保证历史报告解释不变。
export const tailScope=(result:any):"pooled"|"by_station"=>result?.tail?.resample_scope==="by_station"?"by_station":"pooled";
export const scopeLabel=(result:any)=>tailScope(result)==="by_station"?"按站点分层重采样":"跨站混合重采样（原口径）";
export const modeledTailLabel=(result:any)=>tailScope(result)==="by_station"?"站内重采样合并尾分位":"独立重采样尾分位";
export const stationCounts=(result:any):Record<string,number>=>{
 const direct=result?.tail?.station_counts;
 if(direct&&Object.keys(direct).length)return direct;
 const counts:Record<string,number>={};
 for(const row of result?.rows||[])counts[row.station]=(counts[row.station]||0)+1;
 return counts;
};
export const countsText=(result:any)=>{const counts=stationCounts(result);const keys=Object.keys(counts);return keys.length?keys.map(k=>`${k} ${counts[k]}票`).join(" · "):"—"};
