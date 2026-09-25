import numpy as np, soundfile as sf, json
from scipy.ndimage import maximum_filter1d, uniform_filter1d
y, sr = sf.read('song.wav'); y = y.astype(np.float32)
FPS=30; hop=sr//FPS  # 735
n_fft=2048
nfr=len(y)//hop
win=np.hanning(n_fft).astype(np.float32)
pad=np.pad(y,(n_fft//2,n_fft))
S=np.empty((nfr,n_fft//2+1),np.float32)
for i in range(nfr):
    S[i]=np.abs(np.fft.rfft(pad[i*hop:i*hop+n_fft]*win))
f=np.fft.rfftfreq(n_fft,1/sr)
def band(lo,hi): return S[:,(f>=lo)&(f<hi)].sum(1)
bands={'sub':band(20,90),'low':band(90,250),'mid':band(250,2500),'high':band(2500,11000)}
rms=np.sqrt(uniform_filter1d(np.pad(y**2,(0,hop)),hop)[::hop][:nfr])
L=np.log1p(S*10)
flux=np.maximum(0,np.diff(L,axis=0,prepend=L[:1])).sum(1)
def norm(x):
    x=np.asarray(x,float); lo,hi=np.percentile(x,2),np.percentile(x,99.5); return np.clip((x-lo)/(hi-lo+1e-9),0,1)
def onsets(x,k=1.4,minsep=3):
    x=norm(x); m=uniform_filter1d(x,15)
    pk=(x==maximum_filter1d(x,minsep*2+1))&(x>m*k+0.05)&(x>0.12)
    return np.where(pk)[0]
bflux={}
for k,(lo,hi) in {'sub':(20,120),'mid':(150,2500),'high':(3000,11000)}.items():
    Lb=L[:,(f>=lo)&(f<hi)]; bflux[k]=np.maximum(0,np.diff(Lb,axis=0,prepend=Lb[:1])).sum(1)
out={'fps':FPS,'n':int(nfr),'dur':len(y)/sr,
 'rms':norm(rms).round(3).tolist(),
 'flux':norm(flux).round(3).tolist()}
for k,v in bands.items(): out[k]=norm(v).round(3).tolist()
out['on']=onsets(flux).tolist()
for k,v in bflux.items(): out['on_'+k]=onsets(v).tolist()
# tempo via autocorr of flux
x=norm(flux)-norm(flux).mean(); ac=np.correlate(x,x,'full')[len(x)-1:]
lags=np.arange(len(ac)); bpm=60*FPS/np.maximum(lags,1)
ok=(bpm>70)&(bpm<180); lag=lags[ok][np.argmax(ac[ok])]
out['bpm']=60*FPS/lag
json.dump(out,open('feat.json','w'))
print('frames',nfr,'bpm',out['bpm'],'onsets',len(out['on']),{k:len(out['on_'+k]) for k in bflux})
# energy per 5s section
r=norm(rms)
for s in range(0,nfr,FPS*8): print(f"{s/FPS:6.1f}s rms {r[s:s+FPS*8].mean():.2f} sub {norm(bands['sub'])[s:s+FPS*8].mean():.2f} high {norm(bands['high'])[s:s+FPS*8].mean():.2f} ons {sum(1 for o in out['on'] if s<=o<s+FPS*8)}")
