import cv2, numpy as np, sys, os
S=sys.argv[1]
f=cv2.imread(f"{S}/all/189.png")
x0,y0,x1,y1=352,186,640,243
roi=f[y0:y1,x0:x1].astype(int)
mx=roi.max(2); mn=roi.min(2)
txt=((mn>200)&(mx-mn<40)).astype(np.uint8)*255
core=np.zeros(f.shape[:2],np.uint8); core[y0:y1,x0:x1]=txt
mask=cv2.dilate(core,np.ones((9,9),np.uint8))
msmall=cv2.dilate(core,np.ones((5,5),np.uint8))
soft=cv2.GaussianBlur(mask.astype(np.float32)/255,(0,0),2); soft=np.maximum(soft,mask/255.)[...,None]
valid=(mask==0).astype(np.float32)
def nblur(img,s):  # normalized blur ignoring masked pixels
    num=cv2.GaussianBlur(img*valid[...,None],(0,0),s); den=cv2.GaussianBlur(valid,(0,0),s)[...,None]
    return num/np.maximum(den,1e-3)
plate=cv2.imread(f"{S}/all/161.png").astype(np.float32)
pb=nblur(plate,10)
for i in range(157,189):
    fr=cv2.imread(f"{S}/all/{i+1:03d}.png"); frf=fr.astype(np.float32)
    ratio=nblur(frf,10)/np.maximum(pb,1)
    pl=np.clip(plate*ratio,0,255)
    inp=cv2.inpaint(fr,mask,7,cv2.INPAINT_TELEA).astype(np.float32)
    inps=cv2.inpaint(fr,msmall,4,cv2.INPAINT_TELEA).astype(np.float32)
    inps=np.where(msmall[...,None]>0,inps,frf)
    lum=cv2.GaussianBlur(inp.mean(2),(0,0),1.5)   # head/hair is clearly darker than the wall
    w=np.clip((lum-78)/18,0,1)[...,None]
    inp=inps
    fill=w*pl+(1-w)*inp
    sw=soft*w+(1-w)*1.0
    out=sw*fill+(1-sw)*frf
    cv2.imwrite(f"{S}/fixed/{i:03d}.png",np.clip(out+0.5,0,255).astype(np.uint8))
ks=(166,170,176,182,188)
tiles=[cv2.imread(f"{S}/fixed/{k:03d}.png")[150:300,330:700] for k in ks]
orig=[cv2.imread(f"{S}/all/{k+1:03d}.png")[150:300,330:700] for k in ks]
cv2.imwrite(f"{S}/work/protfix.png",np.hstack([np.vstack(orig),np.vstack(tiles)]))
