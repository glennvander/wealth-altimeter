import json, math
HH = 132_000_000          # US households, 2026
POP = 341_000_000
# Fed DFA Q1 2026, $ (millions -> dollars)
G = {"b50": 4_266_359e6, "p50_90": 51_484_864e6, "p90_99": 63_225_396e6,
     "p99_999": 29_960_718e6, "top01": 25_072_282e6}
TOTAL = sum(G.values())
# Sub-brackets inside the top 0.1% (estimates; WID + Forbes)
TOP001 = 14.0e12   # top 0.01% (13,200 hh)
TOP0001 = 10.0e12  # top 0.001% (1,320 hh)
TOP00001 = 6.1e12  # top 0.0001% (132 hh)
NAMED = [("Elon Musk",900,"Tesla, SpaceX, xAI"),("Larry Page",283,"Alphabet"),("Jeff Bezos",270,"Amazon"),
 ("Sergey Brin",261,"Alphabet"),("Michael Dell",255,"Dell"),("Mark Zuckerberg",203,"Meta"),
 ("Jensen Huang",194,"Nvidia"),("Larry Ellison",193,"Oracle"),("Steve Ballmer",152,"Microsoft"),("Warren Buffett",143,"Berkshire Hathaway")]
named_sum = sum(n[1] for n in NAMED)*1e9

# DQYDJ / SCF 2023 thresholds (percentile -> $)
T = {0:-60000, 4:-20000, 8:0, 10:440, 15:5000, 20:13528, 25:27016, 30:51366, 40:110314, 50:192084,
     60:312622, 70:493068, 75:658340, 80:891750, 90:1920758, 95:3779600, 98:8464740,
     99:13666778, 99.5:20149352, 99.9:61827166, 99.99:220e6, 99.999:1.0e9, 99.9999:15e9}
ks = sorted(T)
def thr(p):
    """threshold at percentile p (0..100), interpolating in log(100-p) for top, else linear/log."""
    for i in range(len(ks)-1):
        a,b = ks[i], ks[i+1]
        if a <= p <= b:
            ta,tb = T[a],T[b]
            if ta > 0 and tb > 0:
                if a >= 90:  # log-log in tail
                    xa,xb,x = math.log(100-a+1e-9), math.log(100-b+1e-9), math.log(100-p+1e-9)
                    f = (x-xa)/(xb-xa)
                else:
                    f = (p-a)/(b-a)
                return math.exp(math.log(ta)+f*(math.log(tb)-math.log(ta)))
            f = (p-a)/(b-a); return ta+f*(tb-ta)
    return T[ks[-1]]
def avg(lo,hi,n=64):
    return sum(thr(lo+(hi-lo)*(i+0.5)/n) for i in range(n))/n

# ---- Level 0: 100 percentiles
L0 = [{"lo":i,"hi":i+1,"avg":avg(i,i+1)} for i in range(100)]
def scale(buckets, lo, hi, target):
    sel=[b for b in buckets if b["lo"]>=lo-1e-9 and b["hi"]<=hi+1e-9]
    s=sum(b["avg"]*(b["hi"]-b["lo"])/100*HH for b in sel)
    f=target/s
    for b in sel: b["avg"]*=f
    return f
# Smooth scale factor: piecewise-linear in percentile with knots at the group centres, solved so each
# Fed group total matches exactly (no step at the 50th or 90th percentile boundary).
KN=[25.0,70.0,94.5]
def basis(p):
    """weights of (f1,f2,f3) at percentile centre p"""
    if p<=KN[0]: return (1,0,0)
    if p>=KN[2]: return (0,0,1)
    if p<=KN[1]: t=(p-KN[0])/(KN[1]-KN[0]); return (1-t,t,0)
    t=(p-KN[1])/(KN[2]-KN[1]); return (0,1-t,t)
groups=[(0,50,G["b50"]),(50,90,G["p50_90"]),(90,99,G["p90_99"])]
A=[[0.0]*3 for _ in range(3)]; B=[0.0]*3
for gi,(lo,hi,tot) in enumerate(groups):
    for b in L0[lo:hi]:
        w=basis(b["lo"]+0.5); raw=b["avg"]*0.01*HH
        for k in range(3): A[gi][k]+=raw*w[k]
    B[gi]=tot
# solve 3x3 by Gaussian elimination
M=[A[i]+[B[i]] for i in range(3)]
for c in range(3):
    piv=max(range(c,3),key=lambda r:abs(M[r][c])); M[c],M[piv]=M[piv],M[c]
    for r in range(3):
        if r!=c:
            f=M[r][c]/M[c][c]; M[r]=[x-f*y for x,y in zip(M[r],M[c])]
F=[M[i][3]/M[i][i] for i in range(3)]
for b in L0[:99]:
    w=basis(b["lo"]+0.5); b["avg"]*=sum(F[k]*w[k] for k in range(3))
L0[99]["avg"]=(G["p99_999"]+G["top01"])/(0.01*HH)
f_b50,f_5090,f_9099=F
print("scale factors at knots", [round(x,3) for x in F])
for lo,hi,tot in groups: print("  group",lo,hi,"check", round(sum(b["avg"] for b in L0[lo:hi])*0.01*HH/tot,6))
mono=all(L0[i]["avg"]<=L0[i+1]["avg"] for i in range(99)); print("monotone", mono)
# thresholds scaled with group factors (entry ticket for each percentile)
def thr_scaled(p):
    w=basis(p); return thr(p)*sum(F[k]*w[k] for k in range(3))
for b in L0: b["entry"]=thr(b["lo"])

# ---- deeper levels: geometric profile within bracket, rescaled to bracket total
def sub(lo,hi,n,total,tl,tu):
    step=(hi-lo)/n
    bs=[{"lo":lo+i*step,"hi":lo+(i+1)*step,"avg":tl*(tu/tl)**((i+0.5)/n)} for i in range(n)]
    s=sum(b["avg"]*step/100*HH for b in bs); f=total/s
    for i,b in enumerate(bs): b["avg"]*=f; b["entry"]=tl*(tu/tl)**(i/n)
    return bs
L1=sub(99,99.9,9,G["p99_999"],thr(99),thr(99.9)); L1.append({"lo":99.9,"hi":100,"avg":G["top01"]/(0.001*HH),"entry":thr(99.9)})
L2=sub(99.9,99.99,9,G["top01"]-TOP001,thr(99.9),thr(99.99)); L2.append({"lo":99.99,"hi":100,"avg":TOP001/(0.0001*HH),"entry":thr(99.99)})
L3=sub(99.99,99.999,9,TOP001-TOP0001,thr(99.99),thr(99.999)); L3.append({"lo":99.999,"hi":100,"avg":TOP0001/(0.00001*HH),"entry":thr(99.999)})
L4=sub(99.999,99.9999,9,TOP0001-TOP00001,thr(99.999),thr(99.9999)); L4.append({"lo":99.9999,"hi":100,"avg":TOP00001/(0.000001*HH),"entry":thr(99.9999)})
rest122=(TOP00001-named_sum)/122
L5=[{"name":"Ranks 11–132","hh":122,"total":TOP00001-named_sum,"avg":rest122,"src":"Forbes 400 tail"}]+[{"name":n,"hh":1,"total":v*1e9,"avg":v*1e9,"src":s} for n,v,s in reversed(NAMED)]
# quintile shares (actual 2026)
q=[sum(b["avg"] for b in L0[i*20:(i+1)*20])*0.01*HH/TOTAL*100 for i in range(5)]
print("quintiles bottom->top", [round(x,1) for x in q])
print("median entry", round(thr_scaled(50)), "p1 avg", round(L0[0]["avg"]), "p99 entry", round(L0[99]["entry"]))
for name,L in [("L1",L1),("L2",L2),("L3",L3),("L4",L4)]:
    print(name, [round(b["avg"]/1e6,1) for b in L], "entry", [round(b["entry"]/1e6,1) for b in L])
print("rest122 avg", rest122/1e9)
lookup=[[p,thr(p)] for p in [i for i in range(0,99)]+[99+i/10 for i in range(0,9)]+[99.9+i/100 for i in range(0,9)]+[99.99+i/1000 for i in range(0,9)]+[99.999+i/10000 for i in range(0,10)]]
out={"lookup":lookup,"HH":HH,"POP":POP,"TOTAL":TOTAL,"groups":G,"L0":L0,"L1":L1,"L2":L2,"L3":L3,"L4":L4,"L5":L5,
     "quintiles_actual":q,"scale_factors":[f_b50,f_5090,f_9099]}

# ---- net-worth bands: households and dollars per dollar band
def pct_of(v):
    """percentile (0..100) of a net worth v via the threshold curve"""
    lo,hi=0.0,100.0
    if v<=thr(0): return 0.0
    if v>=thr(99.9999): return 99.9999+0.0001*min(0.999, math.log(v/thr(99.9999))/math.log(900e9/thr(99.9999)))
    for _ in range(60):
        mid=(lo+hi)/2
        if thr(mid)<v: lo=mid
        else: hi=mid
    return (lo+hi)/2
BANDS=[(-1e18,0,"$0 or less"),(0,10e3,"$0–10K"),(10e3,50e3,"$10K–50K"),(50e3,100e3,"$50K–100K"),(100e3,250e3,"$100K–250K"),(250e3,500e3,"$250K–500K"),
       (500e3,1e6,"$500K–1M"),(1e6,2e6,"$1M–2M"),(2e6,5e6,"$2M–5M"),(5e6,10e6,"$5M–10M"),(10e6,50e6,"$10M–50M"),(50e6,250e6,"$50M–250M"),(250e6,1e9,"$250M–1B"),(1e9,1e18,"$1B+")]
# dollars per band: walk the fine bucket structure (percentile buckets, then the top-1% sub-levels) and assign each bucket by its average
fine=[(b["lo"],b["hi"],b["avg"]) for b in L0[:99]]+[(b["lo"],b["hi"],b["avg"]) for b in L1[:9]]+[(b["lo"],b["hi"],b["avg"]) for b in L2[:9]]+[(b["lo"],b["hi"],b["avg"]) for b in L3[:9]]+[(b["lo"],b["hi"],b["avg"]) for b in L4[:9]]
fine+=[(99.9999,99.9999+122/HH*100,rest122)]+[(99.9999,99.9999+1/HH*100,v*1e9) for n,v,src in NAMED]
bands=[]
for lo,hi,lab in BANDS:
    plo=pct_of(lo) if lo>-1e17 else 0.0
    phi=pct_of(hi) if hi<1e17 else 100.0
    hh=(phi-plo)/100*HH
    if lab=="$1B+": hh=1320
    dollars=sum(a*(h-l)/100*HH for l,h,a in fine if (a<=0 if lo<0 else lo<=a<hi))
    if lab=="$1B+": dollars=TOP0001
    bands.append({"lo":lo if lo>-1e17 else None,"hi":hi if hi<1e17 else None,"label":lab,"hh":hh,"dollars":dollars})
# fix the second-to-last band so that the $250M-1B band count is consistent with ~1,320 billionaire households
tot_hh=sum(b["hh"] for b in bands); 
print("band hh total", tot_hh/1e6, [ (b["label"], round(b["hh"]/1e6,2), round(b["dollars"]/1e12,2)) for b in bands])
# ---- income bands (Census HINC-01, income year 2024)
H=json.load(open("hinc01.json")); hdr,row=H["headers"],H["all"]
raw={h:float(v) for h,v in zip(hdr,row) if h.startswith(("Under","$"))}
IHH=float(row[1])*1e3
def rng(a,b): return sum(v for h,v in raw.items() if h.startswith("$") and a<=int(h[1:].split(",")[0]+h[1:].split(",")[1][:3])<b)*1e3
def keyval(h):
    if h.startswith("Under"): return 0
    return int(h[1:].replace(",","").split(" ")[0])
def band_sum(a,b): return sum(v for h,v in raw.items() if a<=keyval(h)<b)*1e3
IB=[(0,15e3,"Under $15K"),(15e3,25e3,"$15K–25K"),(25e3,35e3,"$25K–35K"),(35e3,50e3,"$35K–50K"),(50e3,75e3,"$50K–75K"),(75e3,100e3,"$75K–100K"),(100e3,150e3,"$100K–150K"),(150e3,200e3,"$150K–200K"),(200e3,1e18,"$200K+")]
income_bands=[{"lo":lo,"hi":(hi if hi<1e17 else None),"label":lab,"hh":band_sum(lo,hi if hi<1e17 else 1e18)} for lo,hi,lab in IB]
print("income hh", sum(b["hh"] for b in income_bands)/1e6, IHH/1e6)
out["bands"]=bands; out["income_bands"]=income_bands; out["income"]={"HH":IHH,"median":83730,"mean":121000,
  "ladder":[["Median household",83730,"Census 2024"],["Top 10% entry",251036,"DQYDJ 2025"],["Top 1% entry",659060,"DQYDJ 2025"],["Top 0.1% entry",3.2e6,"Saez, ≈ 2024, incl. capital gains"],["Top 0.01% entry",13e6,"Saez/PSZ, ≈ 2024 est."],["Top 400 average",318e6,"IRS, 2014 (last published)"]]}
json.dump(out,open("model.json","w"))
print("total check", sum(b["avg"] for b in L0)*0.01*HH/1e12)
