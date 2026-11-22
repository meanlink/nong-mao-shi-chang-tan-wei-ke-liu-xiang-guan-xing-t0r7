from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.models import Brief,AnalysisRun,BriefInvalidation
from src.schemas.market import BriefIn
from src.middlewares.auth import current_user,require_roles
from src.services.audit import record
from src.services.lifecycle import brief_invalidation,contaminated_analysis
from src.utils.serialization import brief_dict
router=APIRouter(prefix='/briefs')
def _dict(db:Session,b:Brief):
    return brief_dict(b,brief_invalidation(db,b.id))
@router.get('')
def list_briefs(db:Session=Depends(get_db),u=Depends(current_user)):return [_dict(db,b) for b in db.scalars(select(Brief).order_by(Brief.id.desc()))]
@router.get('/{brief_id}')
def get_brief(brief_id:int,db:Session=Depends(get_db),u=Depends(current_user)):
    b=db.get(Brief,brief_id)
    if not b:raise HTTPException(404,'招商简报不存在')
    return _dict(db,b)
@router.post('',status_code=201)
def create_brief(p:BriefIn,db:Session=Depends(get_db),u=Depends(require_roles('admin','analyst'))):
    # Lock the analysis so a concurrent void cannot slip between these checks
    # and the brief insert.
    a=db.get(AnalysisRun,p.analysis_id,with_for_update=True)
    if not a or a.status!='completed' or a.review_status!='approved' or not a.result or not a.result.get('explainable'):raise HTTPException(409,'只有通过解释性检查并完成运营复核的分析才能生成招商简报')
    if a.status=='invalidated' or contaminated_analysis(db,a):raise HTTPException(409,'该分析包含已报废样本，不能生成招商简报')
    if db.scalar(select(Brief).where(Brief.analysis_id==a.id)):raise HTTPException(409,'该分析已经生成过招商简报')
    rows=a.result.get('stall_findings',[]);summary=f"{a.result.get('headline')}。建议优先关注 {', '.join(x['stall_code'] for x in rows if x['signal']=='优先招商') or '客流稳定但需补采样的摊位'}。"
    b=Brief(analysis_id=a.id,title=p.title,status='draft',summary=summary,recommended_stalls=rows,audience=p.audience);db.add(b);db.flush();record(db,u.email,'brief.created',{'id':b.id,'analysis_id':a.id});db.commit();db.refresh(b);return _dict(db,b)
@router.post('/{brief_id}/issue')
def issue(brief_id:int,db:Session=Depends(get_db),u=Depends(require_roles('admin'))):
    # Lock order is analysis -> brief everywhere (void does the same) to avoid
    # deadlocking a concurrent void against this issue.
    probe=db.get(Brief,brief_id)
    if not probe:raise HTTPException(404,'招商简报不存在')
    a=db.get(AnalysisRun,probe.analysis_id,with_for_update=True)
    b=db.get(Brief,brief_id,with_for_update=True)
    if b.status=='retracted' or brief_invalidation(db,b.id):raise HTTPException(409,'简报已撤回或已停止发出，不能再次发出')
    if b.status!='draft':raise HTTPException(409,'只有草稿状态的招商简报可以发出')
    if not a or a.status=='invalidated' or contaminated_analysis(db,a):raise HTTPException(409,'关联分析包含已报废样本，简报不能发出')
    b.status='issued';b.issued_by=u.id;b.issued_at=datetime.utcnow();record(db,u.email,'brief.issued',{'id':b.id});db.commit();return _dict(db,b)
