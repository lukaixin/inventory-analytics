from __future__ import annotations
import json, uuid
from pathlib import Path
from functools import wraps
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from .db import get_db
from .policy import POLICY
from .models import DatasetSeries, DatasetVersion, ImportBatch
from .services import batch_view, commit_batch, csv_export, evidence_for_version, explore, export_rows, inventory_items, legacy_aging, legacy_dashboard, legacy_mwd, preview, snapshots, source_for_version, template
from .management import analysis as management_analysis, catalog as management_catalog, inventory_table as management_inventory_table, management_export, overview as management_overview

app=FastAPI(title="Inventory Analytics API",version="1.0")
def ok(data, meta=None): return {"data":data,"meta":meta or {}}
def fail(status,code,message,details=None): raise HTTPException(status_code=status,detail={"code":code,"message":message,"details":details or {},"trace_id":str(uuid.uuid4())})
@app.exception_handler(HTTPException)
async def http_error(_,exc):
    d=exc.detail if isinstance(exc.detail,dict) else {"code":"HTTP_ERROR","message":str(exc.detail),"details":{},"trace_id":str(uuid.uuid4())}
    return JSONResponse(status_code=exc.status_code,content={"error":d})
@app.exception_handler(Exception)
async def unexpected(_,exc): return JSONResponse(status_code=500,content={"error":{"code":"INTERNAL_ERROR","message":"服务器处理请求失败","details":{},"trace_id":str(uuid.uuid4())}})
@app.exception_handler(RequestValidationError)
async def request_validation(_,exc): return JSONResponse(status_code=422,content={"error":{"code":"REQUEST_VALIDATION_ERROR","message":"请求参数校验失败","details":{"errors":exc.errors()},"trace_id":str(uuid.uuid4())}})

@app.get("/health/live")
def live(): return {"status":"ok"}
@app.get("/health/ready")
def ready(db:Session=Depends(get_db)):
    try: db.execute(text("select 1")); db.execute(text("select version_num from alembic_version")); return {"status":"ok"}
    except SQLAlchemyError: fail(503,"DATABASE_NOT_READY","数据库或迁移尚未就绪")
@app.get("/api/v1/datasets")
def datasets(db:Session=Depends(get_db)):
    rows=db.scalars(select(DatasetSeries).order_by(DatasetSeries.kind,DatasetSeries.code)).all()
    return ok([{"id":str(x.id),"code":x.code,"title":x.title,"kind":x.kind,"current_version_id":str(x.current_version_id) if x.current_version_id else None} for x in rows])
@app.get("/api/v1/datasets/{series_id}/versions")
def versions(series_id:str,db:Session=Depends(get_db)):
    try:sid=uuid.UUID(series_id)
    except ValueError:fail(422,"INVALID_ID","数据系列ID格式错误")
    if not db.get(DatasetSeries,sid):fail(404,"SERIES_NOT_FOUND","未找到数据系列")
    rows=db.scalars(select(DatasetVersion).where(DatasetVersion.series_id==sid).order_by(DatasetVersion.created_at.desc())).all()
    return ok([{"id":str(x.id),"label":x.label,"evidence_level":x.evidence_level,"schema_version":x.schema_version,"created_at":x.created_at.isoformat() if x.created_at else None,"source_file_id":str(x.source_file_id) if x.source_file_id else None,"limitations":x.limitations} for x in rows])
def guard(fn):
    @wraps(fn)
    def inner(*args,**kwargs):
        try:return fn(*args,**kwargs)
        except KeyError as e:fail(404,str(e).strip("'"),"未找到请求的数据")
        except ValueError as e:fail(422,str(e),"请求参数不属于同一数据系列或格式不正确")
        except PermissionError:fail(403,"SCOPE_DENIED","当前数据授权范围不允许此操作")
    inner.__name__=fn.__name__; return inner
@app.get("/api/v1/legacy/dashboard")
@guard
def dashboard(version_id:str,scope:str|None=None,db:Session=Depends(get_db)): data,m=legacy_dashboard(db,version_id,scope); return ok(data,m)
@app.get("/api/v1/legacy/aging")
@guard
def aging(version_id:str,db:Session=Depends(get_db)): data,m=legacy_aging(db,version_id); return ok(data,m)
@app.get("/api/v1/legacy/mwd")
@guard
def mwd(version_id:str,db:Session=Depends(get_db)): data,m=legacy_mwd(db,version_id); return ok(data,m)
@app.get("/api/v1/sources")
@guard
def sources(version_id:str,db:Session=Depends(get_db)): data,m=source_for_version(db,version_id); return ok(data,m)
@app.get("/api/v1/evidence")
@guard
def evidence(version_id:str,ref:str,db:Session=Depends(get_db)): data,m=evidence_for_version(db,version_id,ref); return ok(data,m)
@app.get("/api/v1/management/catalog")
@guard
def management_catalog_route(version_id:str,db:Session=Depends(get_db)):
    data,m=management_catalog(db,version_id,POLICY); return ok(data,m)
@app.get("/api/v1/management/overview")
@guard
def management_overview_route(version_id:str,scope_id:str="GROUP",material_form:str="ALL",analysis_period:str|None=None,baseline_period:str|None=None,structure_metric:str="turnover_days",db:Session=Depends(get_db)):
    data,m=management_overview(db,version_id,scope_id,material_form,analysis_period,baseline_period,POLICY,structure_metric); return ok(data,m)
@app.get("/api/v1/management/analysis")
@guard
def management_analysis_route(version_id:str,current_alias:str,baseline_alias:str,business_line_id:str|None=None,material_form:str="ALL",db:Session=Depends(get_db)):
    data,m=management_analysis(db,version_id,current_alias,baseline_alias,business_line_id,material_form,POLICY); return ok(data,m)
@app.get("/api/v1/management/inventory-table")
@guard
def management_table_route(version_id:str,snapshot_alias:str,business_line_id:str|None=None,material_form:str="ALL",risk_view:str="all",search:str|None=None,parent_key:str|None=None,sort_by:str="inventory_amount",sort_dir:str="desc",page:int=Query(1,ge=1),size:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    data,m=management_inventory_table(db,version_id,snapshot_alias,business_line_id,material_form,risk_view,search,parent_key,sort_by,sort_dir,page,size,POLICY); return ok(data,m)
@app.get("/api/v1/management/export")
@guard
def management_export_route(version_id:str,snapshot_alias:str,business_line_id:str|None=None,material_form:str="ALL",risk_view:str="all",search:str|None=None,db:Session=Depends(get_db)):
    return Response(management_export(db,version_id,snapshot_alias,business_line_id,material_form,risk_view,search,POLICY),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=management-inventory-export.csv"})
@app.get("/api/v1/inventory/snapshots")
@guard
def inventory_snapshots(version_id:str,db:Session=Depends(get_db)): data,m=snapshots(db,version_id); return ok(data,m)
def filters(pdt=None,customer=None,project=None,material_category=None,search=None): return {"pdt":pdt,"customer":customer,"project":project,"material_category":material_category,"search":search}
@app.get("/api/v1/inventory/items")
@guard
def items(version_id:str,snapshot_id:str,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),pdt:str|None=None,customer:str|None=None,project:str|None=None,material_category:str|None=None,search:str|None=None,db:Session=Depends(get_db)):
    data,m=inventory_items(db,version_id,snapshot_id,page,size,**filters(pdt,customer,project,material_category,search)); return ok(data,m)
@app.get("/api/v1/inventory/explore")
@guard
def inventory_explore(version_id:str,snapshot_id:str,baseline_id:str|None=None,group_by:str="material_category",pdt:str|None=None,customer:str|None=None,project:str|None=None,material_category:str|None=None,search:str|None=None,db:Session=Depends(get_db)):
    data,m=explore(db,version_id,snapshot_id,baseline_id,group_by,**filters(pdt,customer,project,material_category,search)); return ok(data,m)
@app.get("/api/v1/inventory/export")
@guard
def inventory_export(version_id:str,snapshot_id:str,pdt:str|None=None,customer:str|None=None,project:str|None=None,material_category:str|None=None,search:str|None=None,db:Session=Depends(get_db)):
    data,_=export_rows(db,version_id,snapshot_id,**filters(pdt,customer,project,material_category,search)); return Response(csv_export(data),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=inventory-export.csv"})
@app.get("/api/v1/imports/template")
def import_template(): return Response(json.dumps(template(),ensure_ascii=False,indent=2),media_type="application/json",headers={"Content-Disposition":"attachment; filename=canonical_json_v1_template.json"})
@app.post("/api/v1/imports/preview")
async def import_preview(file:UploadFile=File(...),db:Session=Depends(get_db)):
    if not POLICY.import_allowed(): fail(403,"IMPORT_SCOPE_DENIED","受限授权模式不允许导入")
    content=await file.read(5*1024*1024+1)
    try:return ok(batch_view(preview(db,file.filename or "upload.json",content)))
    except OverflowError:fail(413,"FILE_TOO_LARGE","文件超过5MiB限制")
    except ValueError as e:fail(422,"INVALID_IMPORT_FILE",str(e))
@app.get("/api/v1/imports/{import_id}")
def import_status(import_id:str,db:Session=Depends(get_db)):
    if not POLICY.import_allowed(): fail(403,"IMPORT_SCOPE_DENIED","受限授权模式不允许查看导入状态")
    try:b=db.get(ImportBatch,uuid.UUID(import_id))
    except ValueError:fail(422,"INVALID_ID","导入ID格式错误")
    if not b:fail(404,"IMPORT_NOT_FOUND","未找到导入预览")
    return ok(batch_view(b))
@app.post("/api/v1/imports/{import_id}/commit")
def import_commit(import_id:str,body:dict|None=None,db:Session=Depends(get_db)):
    if not POLICY.import_allowed(): fail(403,"IMPORT_SCOPE_DENIED","受限授权模式不允许导入")
    try:b=db.get(ImportBatch,uuid.UUID(import_id))
    except ValueError:fail(422,"INVALID_ID","导入ID格式错误")
    if not b:fail(404,"IMPORT_NOT_FOUND","未找到导入预览")
    try:
        requested=(body or {}).get("set_current",False)
        if type(requested) is not bool: fail(422,"INVALID_SET_CURRENT","set_current必须是布尔值")
        v,already=commit_batch(db,b,requested)
        return ok({"version_id":str(v.id),"series_id":str(v.series_id),"already_committed":already},{"version_id":str(v.id),"evidence_level":v.evidence_level,"limitations":v.limitations})
    except RuntimeError:fail(409,"IMPORT_NOT_COMMITTABLE","导入预览有错误，不能提交")
    except IntegrityError:
        db.rollback(); fail(409,"IMPORT_VERSION_CONFLICT","导入版本标签已存在，请使用新的版本标签")

_dist=Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/",StaticFiles(directory=_dist,html=True),name="frontend")
