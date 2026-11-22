from src.config.database import Base,engine
from src.models import User,Stall,CampaignWindow,FootfallSample,AnalysisRun,Brief,AuditLog,AttributionCorrection,SampleVoid,AnalysisInvalidation,BriefInvalidation
def migrate(): Base.metadata.create_all(bind=engine)
