# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import Base , engine
from backend.routes import image_detect, video_detect, audio_detect , gan_detect , gan_reconstruct, auth , audit , admin , admin_users , forensic_upload , court_verification ,  case , evidence_verify_anchor , admin_evidence_ledger , admin_evidence_anchor_ledger

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DeepFake Forensics API")

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(image_detect.router)
app.include_router(video_detect.router)
app.include_router(audio_detect.router)
app.include_router(gan_detect.router)
app.include_router(gan_reconstruct.router)
app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(admin.router)
app.include_router(admin_users.router)
app.include_router(forensic_upload.router)
app.include_router(court_verification.router)
app.include_router(case.router)
app.include_router(evidence_verify_anchor.router)
app.include_router(admin_evidence_ledger.router)
app.include_router(admin_evidence_anchor_ledger.router)




@app.get("/")
def root():
    return {"message": "DeepFake Forensics API is running!"}
