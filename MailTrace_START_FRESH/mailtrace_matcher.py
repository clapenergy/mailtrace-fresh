# mailtrace_matcher.py — flexible matcher that accepts many header names
import pandas as pd, re

# ------- helpers to normalize headers -------
def _norm_colnames(df):
    return {c: re.sub(r'[^a-z0-9]', '', c.lower()) for c in df.columns}

def _pick(df, aliases):
    nmap = _norm_colnames(df)
    wanted = {re.sub(r'[^a-z0-9]', '', a.lower()): a for a in aliases}
    for real, simple in nmap.items():
        if simple in wanted:
            return real
    return None

def _require(df, aliases, friendly):
    col = _pick(df, aliases)
    if not col:
        raise KeyError(f"{friendly} column not found. Tried: {', '.join(aliases)}")
    return col

# ------- address normalization -------
_ST_TYPE_MAP = {
    "st":"street","ave":"avenue","av":"avenue","blvd":"boulevard","dr":"drive",
    "ln":"lane","rd":"road","trl":"trail","ter":"terrace","cir":"circle",
    "ct":"court","hwy":"highway","pkwy":"parkway","pl":"place","way":"way","sq":"square"
}
_UNIT_KEYS = ["apt","unit","#","ste","suite"]

def _clean_address(a:str)->str:
    if not isinstance(a,str): return ""
    s=a.lower().replace("&"," and ")
    for key in _UNIT_KEYS:
        s=re.sub(rf"\\b{re.escape(key)}\\b\\.?\\s*\\w+","",s)
    s=re.sub(r"[^a-z0-9\\s]"," ",s); s=re.sub(r"\\s+"," ",s).strip()
    parts=s.split()
    if parts:
        last=parts[-1]
        if last in _ST_TYPE_MAP: parts[-1]=_ST_TYPE_MAP[last]
    return " ".join(parts)

def _norm(x): return (str(x or "")).strip().lower()
def _zip5(x):
    z=str(x or "").strip()
    return z[:5] if z else ""

def run_matcher(mail_csv, crm_csv):
    mail=pd.read_csv(mail_csv)
    crm=pd.read_csv(crm_csv)

    # Map FLEXIBLE column names → standard names
    mail_addr = _require(mail,
        ["address","streetaddress","propertyaddress","mailingaddress","addr","address1","street"],
        "Mail CSV address")
    mail_city = _require(mail, ["city","mailcity","propertycity"], "Mail CSV city")
    mail_state= _require(mail, ["state","st","mailstate","propertystate"], "Mail CSV state")
    mail_zip  = _require(mail, ["zip","zipcode","zip_code","postal","postalcode"], "Mail CSV zip")

    crm_addr  = _require(crm,
        ["address","streetaddress","propertyaddress","addr","address1","street"],
        "CRM CSV address")
    crm_city  = _require(crm, ["city"], "CRM CSV city")
    crm_state = _require(crm, ["state","st"], "CRM CSV state")
    crm_zip   = _require(crm, ["zip","zipcode","zip_code","postal","postalcode"], "CRM CSV zip")

    mailed_on = _pick(mail, ["mailed_on","maileddate","sentdate","date"])
    campaign  = _pick(mail, ["campaign_id","campaign","campaignname"])

    first = _pick(crm, ["first_name","firstname","first"])
    last  = _pick(crm, ["last_name","lastname","last"])
    date_entered = _pick(crm, ["date_entered","datecreated","created","lead_date","open_date"])
    job_value    = _pick(crm, ["job_value","revenue","amount","value","jobamount"])

    # Build normalized keys
    mail["_addr"]  = mail[mail_addr].map(_clean_address)
    crm["_addr"]   = crm[crm_addr].map(_clean_address)
    mail["_city"]  = mail[mail_city].map(_norm);   crm["_city"]  = crm[crm_city].map(_norm)
    mail["_state"] = mail[mail_state].map(_norm);  crm["_state"] = crm[crm_state].map(_norm)
    mail["_zip"]   = mail[mail_zip].map(_zip5);    crm["_zip"]   = crm[crm_zip].map(_zip5)

    key=["_zip","_city","_state","_addr"]
    joined = mail.merge(crm, on=key, suffixes=("_mail","_crm"))

    joined["confidence"]=95
    joined["match_notes"]="exact-normalized (addr+city+state+zip)"

    cols=[]
    for c in [
        mail_addr+"_mail", mail_city+"_mail", mail_state+"_mail", mail_zip+"_mail",
        mailed_on, campaign
    ]:
        if c and c in joined.columns: cols.append(c)

    for c in [
        (first or ""), (last or ""), crm_addr+"_crm", crm_city+"_crm", crm_state+"_crm", crm_zip+"_crm",
        date_entered, job_value
    ]:
        if c and c in joined.columns: cols.append(c)

    cols += ["confidence","match_notes"]
    results = joined[cols].copy() if cols else joined.copy()

    total_mail=len(mail); total_crm=len(crm); matches=len(results)
    revenue=float(results.get(job_value, pd.Series(dtype=float)).fillna(0).sum()) if job_value in results.columns else 0.0
    mpa=round(total_mail/matches,2) if matches else None
    kpis={"total_mail":int(total_mail),"total_crm":int(total_crm),"matches":int(matches),
          "revenue_sum":round(revenue,2),"mailers_per_acquisition":mpa}
    return results,kpis
