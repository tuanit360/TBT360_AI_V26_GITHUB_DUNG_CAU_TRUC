"""Trainable pixel-wise softmax classifier; educational baseline, not a production detector.
Uses grayscale and 3x3 pooled neighborhood signals. Labels are per-pixel PNG masks.
Requires independently annotated real projects for meaningful results.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

CATEGORIES = ('background', 'wall', 'door', 'window', 'column')

def _safe_file(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ValueError('Unsafe or missing dataset file')
    return path

def _image(path, mask=False):
    with Image.open(path) as raw:
        raw.load()
        if raw.width * raw.height > 4_000_000 or min(raw.size) < 8:
            raise ValueError('Unsupported image size')
        if mask and raw.mode not in ('L','P'):
            raise ValueError('Mask must contain integer category IDs, not RGB values')
        data=np.asarray(raw.convert('L') if not mask else raw, dtype=np.uint8)
    if mask and np.any(data >= len(CATEGORIES)):
        raise ValueError('Unknown class in mask')
    return data

def features(im):
    a=im.astype(np.float32)/255.0
    padded=np.pad(a,1,mode='edge')
    neighborhood=sum(padded[dy:dy+a.shape[0],dx:dx+a.shape[1]] for dy in range(3) for dx in range(3))/9.0
    dy=np.abs(np.diff(a,axis=0,prepend=a[:1,:]))
    dx=np.abs(np.diff(a,axis=1,prepend=a[:,:1]))
    return np.stack((np.ones_like(a),a,neighborhood,dx,dy),axis=-1).reshape(-1,5)

def load_manifest(root, manifest_name='manifest.json'):
    manifest_path=_safe_file(root,manifest_name)
    payload=json.loads(manifest_path.read_text(encoding='utf-8'))
    rows=payload.get('samples',[])
    if len(rows)<3:
        raise ValueError('At least three annotated samples required')
    projects={'train':set(),'validation':set(),'test':set()}
    seen=set(); prepared=[]
    for row in rows:
        split=row.get('split'); project=row.get('project_id')
        if split not in projects or not isinstance(project,str) or not project.strip():
            raise ValueError('Invalid project/split')
        if row.get('label_status')!='annotated' or row.get('usage_allowed') is not True:
            raise ValueError('Dataset requires explicit labels and use permission')
        image_path=_safe_file(root,row.get('image',''))
        mask_path=_safe_file(root,row.get('mask',''))
        img=_image(image_path);mask=_image(mask_path,True)
        if img.shape!=mask.shape:
            raise ValueError('Image and mask dimensions differ')
        digest=hashlib.sha256(image_path.read_bytes()).hexdigest()
        if digest!=row.get('image_sha256'):
            raise ValueError('Image checksum changed')
        fingerprint=(digest,hashlib.sha256(mask_path.read_bytes()).hexdigest())
        if fingerprint in seen:
            raise ValueError('Exact duplicate sample across dataset')
        seen.add(fingerprint)
        projects[split].add(project)
        prepared.append((split,project,img,mask))
    if any(not value for value in projects.values()):
        raise ValueError('Train, validation and test splits must all exist')
    if any(projects[a]&projects[b] for a,b in (('train','validation'),('train','test'),('validation','test'))):
        raise ValueError('Project leakage across splits')
    return prepared,projects

def scores(y_true,y_pred):
    values={}; intersect=union=0
    for index,name in enumerate(CATEGORIES):
        true=(y_true==index);pred=(y_pred==index)
        tp=int(np.sum(true&pred));fp=int(np.sum(~true&pred));fn=int(np.sum(true&~pred))
        denominator=tp+fp+fn
        values[name]={'iou':round(tp/denominator,6) if denominator else None,
                      'precision':round(tp/(tp+fp),6) if tp+fp else None,
                      'recall':round(tp/(tp+fn),6) if tp+fn else None,
                      'support':int(true.sum())}
        intersect+=tp;union+=denominator
    return {'per_class':values,'micro_iou':round(intersect/union,6) if union else None,
            'pixel_accuracy':round(float(np.mean(y_true==y_pred)),6)}

def train(root,checkpoint,epochs=50,learning_rate=0.7,seed=17):
    if not isinstance(epochs,int) or not 1<=epochs<=500 or not 0<learning_rate<=2:
        raise ValueError('Invalid training hyperparameters')
    records,projects=load_manifest(root)
    xs=[];ys=[]
    for split,_,im,mask in records:
        if split=='train': xs.append(features(im));ys.append(mask.reshape(-1))
    X=np.concatenate(xs);y=np.concatenate(ys)
    rng=np.random.default_rng(seed)
    weights=rng.normal(0,0.01,size=(5,len(CATEGORIES))).astype(np.float32)
    eye=np.eye(len(CATEGORIES),dtype=np.float32)
    counts=np.bincount(y,minlength=len(CATEGORIES)).astype(np.float32)
    class_weights=np.where(counts>0, len(y)/(len(CATEGORIES)*np.maximum(counts,1)),0.0)
    sample_weights=class_weights[y]
    for _ in range(epochs):
        logits=X@weights;logits-=logits.max(axis=1,keepdims=True)
        prob=np.exp(logits);prob/=prob.sum(axis=1,keepdims=True)
        gradient=X.T@((prob-eye[y])*sample_weights[:,None])/max(float(sample_weights.sum()),1.0)
        weights-=learning_rate*gradient.astype(np.float32)
    evaluation={}
    for split in ('train','validation','test'):
        truth=[];prediction=[]
        for row_split,_,im,mask in records:
            if row_split==split:
                truth.append(mask.reshape(-1));prediction.append(np.argmax(features(im)@weights,axis=1))
        evaluation[split]=scores(np.concatenate(truth),np.concatenate(prediction))
    dest=Path(checkpoint);dest.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(dest,weights=weights,classes=np.asarray(CATEGORIES))
    result={'model_type':'trained_pixel_softmax_baseline','not_a_bim_detector':True,
            'splits':{k:sorted(v) for k,v in projects.items()},'metrics':evaluation,
            'checkpoint_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
            'checkpoint':str(dest),'epochs':epochs,'seed':seed}
    return result

def infer(image_path,checkpoint,output):
    with np.load(checkpoint,allow_pickle=False) as saved:
        weight=saved['weights'];classes=saved['classes']
    if weight.shape!=(5,len(CATEGORIES)) or list(classes)!=list(CATEGORIES):
        raise ValueError('Incompatible checkpoint')
    image=_image(image_path)
    classification=np.argmax(features(image)@weight,axis=1).astype(np.uint8).reshape(image.shape)
    Image.fromarray(classification,mode='L').save(output)
    return {'mask':str(output),'classes':list(CATEGORIES),'verification':'unverified_model_prediction'}
