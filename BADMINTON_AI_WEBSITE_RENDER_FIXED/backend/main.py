
import os, uuid, math, json, shutil
from pathlib import Path
import cv2, numpy as np
import subprocess
from imageio_ffmpeg import get_ffmpeg_exe
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO

BASE=Path(__file__).resolve().parent.parent
DATA=BASE/"data"; DATA.mkdir(exist_ok=True)
UPLOAD=DATA/"uploads"; OUT=DATA/"outputs"; CLIPS=DATA/"clips"
for p in (UPLOAD,OUT,CLIPS): p.mkdir(exist_ok=True)

app=FastAPI(title="Badminton AI Smash")
app.mount("/media",StaticFiles(directory=str(OUT)),name="media")
app.mount("/clips",StaticFiles(directory=str(CLIPS)),name="clips")

# YOLO will download the small pretrained model on first startup if needed.
PLAYER_MODEL=os.getenv("PLAYER_MODEL","yolo11n.pt")
player_model=YOLO(PLAYER_MODEL)

def people(result):
    arr=[]
    if result.boxes is None: return arr
    for b in result.boxes:
        if int(b.cls[0])!=0: continue
        c=float(b.conf[0])
        if c<0.35: continue
        x1,y1,x2,y2=b.xyxy[0].cpu().numpy()
        arr.append((int(x1),int(y1),int(x2),int(y2),c))
    return arr

def shuttle_candidates(frame):
    # Lightweight fallback detector for a bright shuttle-sized object.
    # For production accuracy, replace with a trained shuttle YOLO model.
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,np.array([0,0,150]),np.array([180,100,255]))
    mask=cv2.medianBlur(mask,3)
    n,lab,stats,cent=cv2.connectedComponentsWithStats(mask)
    cand=[]
    h,w=frame.shape[:2]
    for i in range(1,n):
        x,y,ww,hh,area=stats[i]
        if 2<=ww<=28 and 2<=hh<=28 and 3<=area<=300:
            cx,cy=cent[i]
            if 0.05*w<cx<0.95*w and 0.05*h<cy<0.95*h:
                cand.append((cx,cy,area))
    return cand

def nearest_to_players(pt, players, pad=130):
    if pt is None: return False
    x,y=pt
    for x1,y1,x2,y2,c in players:
        if x1-pad<=x<=x2+pad and y1-pad<=y<=y2+pad:
            return True
    return False

def speed_from_track(track, fps):
    if len(track)<3 or fps<=0: return 0.0
    vals=[]
    for (f1,x1,y1),(f2,x2,y2) in zip(track[:-1],track[1:]):
        dt=(f2-f1)/fps
        if dt<=0: continue
        # Pixel speed. Converted to km/h using a conservative default scene scale.
        # User calibration can replace PIXELS_PER_METER below.
        ppm=120.0
        meters=((x2-x1)**2+(y2-y1)**2)**0.5/ppm
        vals.append(meters/dt*3.6)
    if not vals: return 0.0
    return float(np.percentile(np.clip(vals,0,450),90))

def draw(frame, players, shuttle, speed=None, smash=False):
    out=frame.copy()
    for x1,y1,x2,y2,c in players:
        cv2.rectangle(out,(x1,y1),(x2,y2),(0,0,255),3)
        cv2.putText(out,f"PLAYER {c:.2f}",(x1,max(22,y1-8)),
                    cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
    if shuttle:
        x,y=map(int,shuttle)
        cv2.rectangle(out,(x-10,y-10),(x+10,y+10),(255,220,0),2)
        cv2.circle(out,(x,y),3,(255,220,0),-1)
        cv2.putText(out,"SHUTTLE",(x+14,y-8),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,220,0),2)
    if speed is not None:
        cv2.rectangle(out,(out.shape[1]-265,18),(out.shape[1]-15,90),(15,25,22),-1)
        cv2.putText(out,f"{speed:.1f} km/h",(out.shape[1]-245,62),
                    cv2.FONT_HERSHEY_SIMPLEX,.95,(255,255,255),2)
    if smash:
        cv2.putText(out,"SMASH",(25,55),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0,255,255),3)
    return out

def analyze_video(src, job):
    cap=cv2.VideoCapture(str(src))
    if not cap.isOpened(): raise RuntimeError("Không mở được video")
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 30)
    w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    # Write a temporary OpenCV file first, then transcode to browser-compatible H.264.
    temp_out=OUT/f"{job}_raw.mp4"
    out_path=OUT/f"{job}.mp4"
    writer=cv2.VideoWriter(str(temp_out),cv2.VideoWriter_fourcc(*"mp4v"),fps,(w,h))
    if not writer.isOpened():
        raise RuntimeError("Không tạo được file video tạm")

    history=[]
    events=[]
    last_event=-9999
    idx=0
    while True:
        ok,frame=cap.read()
        if not ok: break
        pr=player_model.predict(frame,verbose=False,conf=.35)[0]
        pls=people(pr)

        cand=shuttle_candidates(frame)
        shuttle=None
        if cand:
            # Prefer candidate close to a player and closest to previous point.
            if history:
                px,py=history[-1][1],history[-1][2]
                cand.sort(key=lambda q:(q[0]-px)**2+(q[1]-py)**2)
            else:
                cand.sort(key=lambda q:-q[2])
            q=cand[0]; shuttle=(q[0],q[1])

        if shuttle:
            history.append((idx,shuttle[0],shuttle[1]))
            if len(history)>20: history.pop(0)

        smash=False; speed=None
        if len(history)>=5 and idx-last_event>max(8,int(fps*.35)):
            recent=history[-5:]
            # Sudden acceleration + proximity to player is a contact candidate.
            v1=math.dist((recent[0][1],recent[0][2]),(recent[1][1],recent[1][2]))
            v2=math.dist((recent[2][1],recent[2][2]),(recent[3][1],recent[3][2]))
            v3=math.dist((recent[3][1],recent[3][2]),(recent[4][1],recent[4][2]))
            if nearest_to_players(shuttle,pls) and v3>max(12,v1*1.8) and v3>v2*1.25:
                speed=speed_from_track(recent,fps)
                # Avoid physically implausible false positives.
                if 80<=speed<=450:
                    smash=True
                    last_event=idx
                    pre=max(0,idx-int(fps*1.0)); post=min(total-1,idx+int(fps*2.0))
                    events.append({"id":len(events)+1,"frame":idx,"time":idx/fps,
                                   "speed_kmh":round(speed,1),"confidence":.55,
                                   "start_frame":pre,"end_frame":post})

        if events and not smash and idx-events[-1]["frame"]<int(fps*.8):
            speed=events[-1]["speed_kmh"]
        writer.write(draw(frame,pls,shuttle,speed,smash))
        idx+=1

    cap.release(); writer.release()

    # Chrome/Edge/Safari often cannot play OpenCV's MPEG-4 Part 2 output reliably.
    # Convert the analyzed video to H.264 + yuv420p for broad browser compatibility.
    ffmpeg=get_ffmpeg_exe()
    cmd=[ffmpeg,"-y","-i",str(temp_out),"-c:v","libx264","-preset","veryfast","-crf","22",
         "-pix_fmt","yuv420p","-movflags","+faststart","-an",str(out_path)]
    proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    temp_out.unlink(missing_ok=True)
    if proc.returncode!=0 or not out_path.exists() or out_path.stat().st_size<1024:
        raise RuntimeError("Không mã hóa được video H.264: "+proc.stderr[-1200:])

    # Create review clips around every detected smash.
    for e in events:
        cap=cv2.VideoCapture(str(src))
        cap.set(cv2.CAP_PROP_POS_FRAMES,e["start_frame"])
        raw_clip=CLIPS/f"{job}_smash_{e['id']}_raw.mp4"
        clip=CLIPS/f"{job}_smash_{e['id']}.mp4"
        cw=cv2.VideoWriter(str(raw_clip),cv2.VideoWriter_fourcc(*"mp4v"),fps,(w,h))
        for f in range(e["start_frame"],e["end_frame"]+1):
            ok,fr=cap.read()
            if not ok: break
            # simple event marker
            if f==e["frame"]:
                cv2.putText(fr,f"SMASH {e['speed_kmh']:.1f} km/h",(25,55),
                            cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,255),3)
            cw.write(fr)
        cap.release(); cw.release()
        ccmd=[ffmpeg,"-y","-i",str(raw_clip),"-c:v","libx264","-preset","veryfast","-crf","22",
              "-pix_fmt","yuv420p","-movflags","+faststart","-an",str(clip)]
        cproc=subprocess.run(ccmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        raw_clip.unlink(missing_ok=True)
        if cproc.returncode!=0 or not clip.exists():
            raise RuntimeError("Không mã hóa được clip smash: "+cproc.stderr[-800:])
        e["clip_url"]=f"/clips/{clip.name}"

    return {"job_id":job,"video_url":f"/media/{out_path.name}",
            "fps":fps,"frames":total,"duration":total/fps if fps else 0,
            "events":events,"max_speed_kmh":max([e["speed_kmh"] for e in events],default=None),
            "note":"Tốc độ là ước lượng từ video. Muốn đo chính xác cần model shuttle/racket/contact và calibration camera."}

@app.get("/")
def index(): return FileResponse(str(BASE/"frontend/index.html"))

@app.post("/api/analyze")
async def api_analyze(video:UploadFile=File(...)):
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(400,"File không phải video")
    job=uuid.uuid4().hex
    suffix=Path(video.filename or ".mp4").suffix or ".mp4"
    src=UPLOAD/f"{job}{suffix}"
    with open(src,"wb") as f: shutil.copyfileobj(video.file,f)
    try:
        return analyze_video(src,job)
    except Exception as e:
        raise HTTPException(500,str(e))
    finally:
        src.unlink(missing_ok=True)
