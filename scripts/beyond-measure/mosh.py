# Real datamosh: MPEG-4 Part 2 elementary streams, drop I-VOPs of the incoming shot, repeat P-VOPs for bloom.
import subprocess, glob, random, os, sys
os.makedirs('mosh', exist_ok=True)
def enc(src, out):
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-vf','scale=1280:720','-c:v','mpeg4','-q:v','3',
        '-g','9999','-bf','0','-sc_threshold','1000000000','-f','m4v',out],check=True)
def vops(data):
    # split into header (before first VOP) and list of VOPs
    idx=[]; i=data.find(b'\x00\x00\x01\xb6')
    while i!=-1: idx.append(i); i=data.find(b'\x00\x00\x01\xb6',i+4)
    head=data[:idx[0]]; idx.append(len(data))
    return head,[data[idx[k]:idx[k+1]] for k in range(len(idx)-1)]
def vtype(v): return v[4]>>6  # 0=I 1=P 2=B
def make(n, a, b, c=None, mode='drag', seed=0):
    rnd=random.Random(seed)
    ha,va=vops(open(a,'rb').read()); _,vb=vops(open(b,'rb').read())
    out=[ha]+va[:rnd.randint(25,60)]
    pb=[v for v in vb if vtype(v)==1]
    if mode=='bloom':
        # play a little of b's motion, then repeat one P-VOP to make pixels bloom/melt
        out+=pb[:rnd.randint(4,15)]
        k=rnd.randint(15,min(60,len(pb)-1)); out+=[pb[k]]*rnd.randint(25,45)+pb[k+1:k+20]
    else:
        out+=pb[:90]
    if c:
        _,vc=vops(open(c,'rb').read()); out+=[v for v in vc if vtype(v)==1][:45]
    open(f'mosh/m{n}.m4v','wb').write(b''.join(out))
    subprocess.run(['ffmpeg','-v','quiet','-y','-err_detect','ignore_err','-i',f'mosh/m{n}.m4v','-an','-c:v','libx264','-crf','16','-preset','veryfast','-pix_fmt','yuv420p',f'mosh/mosh_{n:02d}.mp4'])
    os.remove(f'mosh/m{n}.m4v')
if __name__=='__main__':
    clips=sorted(glob.glob('clips/*.mp4')); rnd=random.Random(7)
    os.makedirs('m4v',exist_ok=True)
    N=int(sys.argv[1]) if len(sys.argv)>1 else 24
    for n in range(N):
        a,b,c=rnd.sample(clips,3); fs=[]
        for s in (a,b,c):
            o='m4v/'+os.path.basename(s)[:-4]+'.m4v'
            if not os.path.exists(o): enc(s,o)
            fs.append(o)
        make(n,fs[0],fs[1],fs[2] if rnd.random()<0.5 else None,mode=rnd.choice(['drag','bloom','bloom']),seed=n)
        print(n,flush=True)
