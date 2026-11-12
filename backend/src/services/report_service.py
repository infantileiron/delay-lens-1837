import csv,io
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from ..models.review import ActionReview
from ..models.run import DelayRun
from ..models.report import Report

def create(db,body):
 review=db.get(ActionReview,body.review_id)
 if review is None or review.state!="approved":raise HTTPException(409,"报告必须关联已批准的复核")
 existing=db.scalar(select(Report).where(Report.review_id==body.review_id))
 if existing:return existing
 run=db.get(DelayRun,review.run_id);row=Report(id=str(uuid4()),review_id=review.id,title=body.title,snapshot={"result":run.result,"action":review.action,"reviewer":review.reviewer});db.add(row);db.commit();return row

def station_counts(result):
 counts=result["tail"].get("station_counts")
 if counts:return counts
 derived={}
 for r in result.get("rows",[]):derived[r["station"]]=derived.get(r["station"],0)+1
 return dict(sorted(derived.items()))

def export(row):
 out=io.StringIO();writer=csv.writer(out);writer.writerow(["phase","p50_minutes","p90_minutes","p95_minutes","tail_reduction_minutes","share","bootstrap_low","bootstrap_high"])
 result=row.snapshot["result"];tail=result["tail"];contrib={c["phase"]:c for c in tail["contributions"]}
 for p in result["phases"]:
  c=contrib[p["phase"]];writer.writerow([p["phase"],p["p50"],p["p90"],p["p95"],c["reduction"],c["share"],c["low"],c["high"]])
 writer.writerow([]);writer.writerow(["resample_scope",tail.get("resample_scope","pooled")])
 writer.writerow(["station_counts",";".join(f"{k}={v}" for k,v in station_counts(result).items())])
 writer.writerow(["observed_tail",tail["observed_tail"]]);writer.writerow(["modeled_tail",tail["modeled_tail"]])
 return "\ufeff"+out.getvalue()
