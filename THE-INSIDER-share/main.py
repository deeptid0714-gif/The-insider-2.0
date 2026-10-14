"""THE INSIDER — deterministic investigation engine with optional OpenAI dialogue."""
from __future__ import annotations

import os, re, uuid, json
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="THE INSIDER", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

NPCS = {
 "ravi":{"name":"Ravi Mehta","role":"IT Administrator","initials":"RM","color":"#79a9ff","personality":"precise, defensive, technically sharp, and increasingly uneasy","knowledge":"Ravi knows the server access logs, maintenance schedule, his own badge use, and that he copied the file to a USB while trying to expose Mark's illegal sale of employee data. He knows no private conversations between Sarah and Mark.","secret":"He accessed the server at 10:42 PM and copied the file to a USB to preserve proof of Mark's planned data sale. He deleted an audit row to hide the copy, not to cover the original theft."},
 "sarah":{"name":"Sarah Chen","role":"People Operations","initials":"SC","color":"#f2b36f","personality":"observant, confident, dryly funny, and socially perceptive","knowledge":"Sarah saw Ravi near the server room at 10:40 PM and noticed him carrying a small metal USB. She heard Mark push to bury an employee-data export. She does not know what was on the USB or the exact server log time.","secret":"She initially withholds that she saw Ravi because she fears retaliation; she opens up if asked respectfully or shown the badge record."},
 "mark":{"name":"Mark Ellison","role":"Department Manager","initials":"ME","color":"#f08b86","personality":"authoritative, polished, impatient, and controlling","knowledge":"Mark knows the confidential employee file was scheduled for an unauthorized sale to a data broker. He knows the file was opened at 10:47 PM and had authorized access. He does not know Sarah witnessed Ravi.","secret":"He ordered the data export and wants the investigation closed before the morning board meeting."},
 "alex":{"name":"Alex Rivera","role":"Security Technician","initials":"AR","color":"#7fd1b2","personality":"straightforward, nervous, and quietly helpful","knowledge":"Alex knows the camera feed briefly looped at 10:39 PM after a manual override from Mark's office. He knows the badge reader recorded Ravi at 10:42 PM. He does not know the file contents or why Ravi was there.","secret":"Alex kept a maintenance note about Mark's camera override but feared losing his job."}
}
EVIDENCE = {
 "server_log":{"title":"Server access log","detail":"Employee data file opened at 10:47 PM. The access originated from an authorized admin session.","source":"CASE FILE"},
 "badge_record":{"title":"Badge record: Ravi","detail":"Ravi's badge entered the server corridor at 10:42 PM, five minutes before the file was opened.","source":"ALEX · SECURITY"},
 "sarah_witness":{"title":"Witness statement","detail":"Sarah saw Ravi near the server room carrying a metal USB at about 10:40 PM.","source":"SARAH · INTERVIEW"},
 "camera_loop":{"title":"Camera loop","detail":"A camera feed was manually looped at 10:39 PM. The override came from Mark's office.","source":"ALEX · MAINTENANCE NOTE"},
 "deleted_record":{"title":"Deleted audit row","detail":"A 10:49 PM audit entry was removed from the server log after the file was opened.","source":"RAVI · INTERVIEW"},
 "motive":{"title":"The real motive","detail":"Mark planned to sell employee data. Ravi copied it to preserve proof and expose the scheme.","source":"MARK · INTERVIEW"}
}
STATE_FILE = os.path.join(os.path.dirname(__file__), "case_sessions.json")
try:
 with open(STATE_FILE, encoding="utf-8") as f: SESSIONS: dict[str, dict[str, Any]] = json.load(f)
except (OSError, json.JSONDecodeError): SESSIONS = {}

def persist():
 with open(STATE_FILE, "w", encoding="utf-8") as f: json.dump(SESSIONS, f, ensure_ascii=False)

def fresh_state():
 return {"evidence":[],"trust":{"ravi":48,"sarah":48,"mark":42,"alex":48},"interviews":[],"memory":{k:{"questions":[],"revealed":[]} for k in NPCS},"history":[],"ending":None,"turns":0}
class Talk(BaseModel):
 session_id: str
 npc_id: str
 message: str = Field(min_length=1,max_length=600)
class Accuse(BaseModel):
 session_id: str
 suspect_id: str
 reason: str = ""

def contains(text: str, *terms: str) -> bool: return any(t in text for t in terms)

def process(s: dict, who: str, msg: str) -> tuple[str,list[str],int,str]:
 q=msg.lower(); found=[]; delta=0; intent="general"
 repeat=sum(1 for x in s["memory"][who]["questions"] if x.lower()==q)>0
 respectful=contains(q,"please","thank","appreciate","help me understand","honestly")
 aggressive=contains(q,"you stole","you're lying","threat","confess","liar","stole it")
 delta += -2 if repeat else (2 if respectful else (-6 if aggressive else 0))
 if repeat: lead="You already asked me that. Repeating it won't make the answer better. "
 elif aggressive: lead="Don't come at me with an accusation and expect a conversation. "
 else: lead=""
 # shared opening evidence comes from briefing; discovery remains conversational
 if who=="ravi":
  if contains(q,"badge","10:42","access record","accessed the server","server room") and "badge_record" in s["evidence"]:
   intent="evidence"; delta+=3; found += ["deleted_record"]
   if contains(q,"why","usb","copy","copied","motive") and ("sarah_witness" in s["evidence"] or s["trust"][who]>=55):
    intent="secret"; delta+=5; found += ["motive"]
    reply="That was my badge. I copied the file to a USB because Mark was preparing to sell employee data, and I needed proof before it disappeared. I deleted the later audit row because I panicked. I wasn't trying to profit from it."
   else: reply="That was my badge. I was there, yes. The access log doesn't tell you what I was trying to do. I removed a later audit row because I copied something I shouldn't have. I needed the file intact."
  elif contains(q,"why","motive","usb","flash drive","copied","what happened") and ("sarah_witness" in s["evidence"] or s["trust"][who]>=55):
   intent="secret"; found += ["deleted_record"]; delta+=5
   reply="I copied the file to a USB. Mark was preparing to sell employee data, and I wanted proof before he could make it disappear. I deleted my own audit row because I panicked. I didn't steal it for money."
  elif contains(q,"where","10:30","last night","10:40","10:42"):
   intent="timeline"; reply="I was in the IT room most of the evening. I did go to the server corridor around 10:42. It was maintenance—nothing more. (He looks away.)"
  elif contains(q,"mark","manager","sale","sell","employee data"):
   intent="knowledge"; found += ["motive"]; reply="Mark had been pushing an employee-data export for weeks. I can't prove what he planned to do with it. Check with him about the authorization."
  elif contains(q,"sarah"):
   intent="boundary"; reply="I don't know what Sarah saw. You should ask her yourself."
  else: reply="I can tell you about server access, maintenance, and the audit trail. Ask me about the 10:47 access or my badge, if that's what this is about."
 elif who=="sarah":
  if contains(q,"ravi","server","usb","badge","10:40","what did you see","witness"):
   intent="witness"; found += ["sarah_witness"]
   if "badge_record" in s["evidence"] or respectful or s["trust"][who]>=55:
    delta+=5; reply="All right. I saw Ravi near the server room around 10:40, holding a little metal USB. I kept quiet because Mark has made it clear who gets protected here. I didn't see what was on it."
   else: reply="I noticed people moving around that corridor. Why are you asking me specifically about Ravi?"
  elif contains(q,"mark","manager","sell","sale","data"):
   intent="knowledge"; found += ["motive"]; reply="Mark wanted that employee-data export pushed through before the board meeting. He called it a 'commercial opportunity.' I don't know what he actually did with it."
  elif contains(q,"alex","camera","security"):
   intent="boundary"; reply="Alex handles the cameras. I don't have access to those logs."
  else: reply="I notice more than people think. Ask me about the server corridor, or what Mark was pushing for before the board meeting."
 elif who=="mark":
  if contains(q,"camera","loop","override","10:39") and "camera_loop" in s["evidence"]:
   intent="evidence"; delta-=4; reply="Security maintenance is not your concern. The camera loop was a routine override. Let's keep this focused on the missing file."
  elif contains(q,"file","employee","sale","sell","data","motive"):
   intent="motive"; found += ["motive"]; delta-=2
   reply="The employee-data file was part of a commercial review I authorized. I won't pretend the optics are good. But Ravi had administrator access and an unusual interest in those records."
  elif contains(q,"ravi","who accessed","culprit","badge"):
   intent="deflection"; reply="Ravi is the administrator. He had the access and the technical ability. I suggest you follow the evidence rather than office gossip."
  else: reply="I have a company to run and a board meeting in the morning. Ask a direct question about the file or who had authorization."
 else:
  if contains(q,"badge","ravi","10:42","server","access"):
   intent="badge"; found += ["badge_record"]; delta+=4
   reply="The badge reader shows Ravi entering the server corridor at 10:42 PM. The file opened at 10:47. There's also a maintenance note I kept—camera three looped at 10:39, manually overridden from Mark's office."
   found += ["camera_loop"]
  elif contains(q,"camera","loop","override","10:39"):
   intent="camera"; found += ["camera_loop"]; delta+=4; reply="Camera three looped at 10:39 PM. The manual override came from Mark's office. I wrote it down, but I didn't want to get dragged into this."
  elif contains(q,"mark","office"):
   intent="boundary"; reply="I only have access logs and camera maintenance notes. For what Mark was doing, ask him."
  else: reply="I handle building access and camera maintenance. Ask me about the badge reader or camera three. I don't know what was on the stolen file."
 return lead+reply, found, delta, intent

async def polish(npc_id: str, message: str, draft: str, s: dict) -> str:
 key=os.getenv("OPENAI_API_KEY")
 if not key: return draft
 try:
  from openai import AsyncOpenAI
  client=AsyncOpenAI(api_key=key)
  npc=NPCS[npc_id]
  resp=await client.chat.completions.create(model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),temperature=.55,max_tokens=130,
   messages=[{"role":"system","content":f"Write one natural, concise in-character line for {npc['name']}, {npc['role']}. Personality: {npc['personality']}. Canonical known facts: {npc['knowledge']}. Respond to player: {message!r}. This is the approved factual response and may not be contradicted or expanded: {draft!r}. Preserve its exact facts and uncertainty. Never invent clues, facts, or knowledge. You may only lightly rephrase. Keep under 55 words."},{"role":"user","content":"Return only the NPC's dialogue."}])
  return (resp.choices[0].message.content or draft).strip()
 except Exception: return draft

def snapshot(s:dict):
 clues=[{"id":k,**EVIDENCE[k]} for k in s["evidence"]]
 progress=min(100,round(len(s["evidence"])/6*75 + len(s["interviews"])/4*25))
 return {"evidence":clues,"trust":s["trust"],"interviews":s["interviews"],"progress":progress,"ending":s["ending"],"turns":s["turns"],"api_enabled":bool(os.getenv("OPENAI_API_KEY"))}
@app.get("/api/health")
def health(): return {"ok":True,"openai_configured":bool(os.getenv("OPENAI_API_KEY"))}
@app.post("/api/game")
def new_game():
 sid=str(uuid.uuid4()); s=fresh_state(); s["evidence"]=["server_log"]; SESSIONS[sid]=s
 persist()
 return {"session_id":sid,"state":snapshot(s),"npcs":[{"id":k,"name":v["name"],"role":v["role"],"initials":v["initials"],"color":v["color"]} for k,v in NPCS.items()]}
@app.get("/api/game/{sid}")
def load_game(sid:str):
 if sid not in SESSIONS: raise HTTPException(404,"Investigation not found")
 return {"session_id":sid,"state":snapshot(SESSIONS[sid]),"npcs":[{"id":k,"name":v["name"],"role":v["role"],"initials":v["initials"],"color":v["color"]} for k,v in NPCS.items()]}
@app.post("/api/talk")
async def talk(req:Talk):
 if req.session_id not in SESSIONS: raise HTTPException(404,"Investigation expired. Start a new case.")
 if req.npc_id not in NPCS: raise HTTPException(404,"Suspect not found")
 s=SESSIONS[req.session_id]
 if s["ending"]: raise HTTPException(409,"The case is closed. Start a new investigation to continue.")
 npc=req.npc_id; msg=req.message.strip()
 draft,found,delta,intent=process(s,npc,msg)
 s["trust"][npc]=max(0,min(100,s["trust"][npc]+delta))
 for e in found:
  if e in EVIDENCE and e not in s["evidence"]: s["evidence"].append(e)
 if npc not in s["interviews"]: s["interviews"].append(npc)
 mem=s["memory"][npc]; mem["questions"].append(msg); mem["questions"]=mem["questions"][-12:]
 mem["revealed"] += [e for e in found if e not in mem["revealed"]]
 s["turns"]+=1
 reply=await polish(npc,msg,draft,s)
 s["history"].append({"npc":npc,"question":msg,"reply":reply,"intent":intent})
 persist()
 return {"reply":reply,"npc_id":npc,"trust_delta":delta,"new_evidence":[{"id":e,**EVIDENCE[e]} for e in found if e in s["evidence"]],"memory_note":f"{NPCS[npc]['name']} remembers this exchange.","state":snapshot(s)}
@app.post("/api/accuse")
def accuse(req:Accuse):
 if req.session_id not in SESSIONS: raise HTTPException(404,"Investigation expired")
 s=SESSIONS[req.session_id]
 if req.suspect_id not in NPCS: raise HTTPException(400,"Choose a suspect")
 if s["ending"]: return s["ending"]
 if len(s["evidence"])<3: result={"type":"insufficient","title":"Not enough to close the case","message":"You need at least three pieces of evidence before making a defensible accusation.","culprit":None}
 elif req.suspect_id=="ravi": result={"type":"solved","title":"CASE SOLVED · THE INSIDER","message":"Ravi was the person who accessed and copied the file. He deleted his own audit row and concealed the USB, so he is responsible for the breach. The motive evidence changes the story: he copied it to preserve proof of Mark's planned sale of employee data. You found both the act and the reason behind it.","culprit":"ravi","motive":"Ravi copied the file to preserve evidence of Mark's planned sale of employee data. He deleted his own audit entry in a panic.","missed":[x for x in EVIDENCE if x not in s["evidence"]]}
 else: result={"type":"wrong","title":"WRONG ACCUSATION","message":"The evidence places Ravi at the server and identifies him as the person who copied the file. Mark's camera override and planned sale explain the motive, but do not change who accessed the file. Revisit the badge record and witness statement.","culprit":"ravi","motive":"Ravi copied the file to expose Mark's planned sale of employee data.","missed":[x for x in EVIDENCE if x not in s["evidence"]]}
 if result["type"] != "insufficient":
  s["ending"]=result
 persist(); return result
app.mount("/",StaticFiles(directory=os.path.join(os.path.dirname(__file__),"static"),html=True),name="static")
