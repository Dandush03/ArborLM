"""Rung chosen vs common speed factor x when the recomputation IS charged inside R (counterfactual). python3 -I"""
store=(5,10); lora=(8,15); sc=(1.6,5.2); oth=(0.9,3.0); fx=(0.3,0.6); g=(4*1.6/60, 4*5.2/60+0.05)
def R(n,U,i,charged):
    f=1 if U==2000 else .5
    r=n*16*store[i]/60*f+n*6*lora[i]/60*f+n*18*sc[i]/60+n*oth[i]+fx[i]+g[i]
    return r+(n*18*sc[i]/60+n*oth[i]+fx[i] if charged else 0)
rungs=[(4,2000),(3,2000),(4,1000),(3,1000)]
for charged in (False,True):
  for P in (3.5,7.0):
    seg=[];prev=None
    for k in range(1001):
        x=k/1000
        ch=next((j+1 for j,(n,U) in enumerate(rungs) if P+2*(R(n,U,0,charged)+x*(R(n,U,1,charged)-R(n,U,0,charged)))<=36),'NOT STARTED')
        if ch!=prev: seg.append((x,ch)); prev=ch
    print('charged' if charged else 'uncharged', 'P=',P, seg)
