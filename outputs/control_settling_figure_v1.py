"""A derived analytical illustration; no experiments or legacy checks rerun.

--data-only creates exact rational-grid values. --export is allowed only after
the rendered preview has been visually checked. Plotted irrational endpoints
are approximations; exact rankings belong to the referenced Fraction certificate.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import csv
import json
import sys
import math

OUT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--data-only',action='store_true')
parser.add_argument('--export',action='store_true')
args=parser.parse_args()
gamma=F(81,100)
def kappa(c,k):
    aa=sum(c**j for j in range(k+1))
    bb=sum(c**(2*j) for j in range(k+1))
    return k+1-aa*aa/bb
def recover(c):
    s=1
    while c**s>gamma:
        s+=1
    return s

data=OUT/'control_settling_figure_data_v1.csv'
if args.data_only:
    rows=[]
    for i in range(600):
        c=F(4,5)+F(i,4000)
        for mode,k in [('fixed_k1',1),('homogeneous_qualified',recover(c))]:
            kap=kappa(c,k)
            rows.append(dict(c=float(c),c_fraction=str(c),mode=mode,k=k,
                kappa=float(kap),kappa_fraction=str(kap)))
    c=F(19,20)
    for mode,k in [('fixed_k1',1),('homogeneous_qualified',recover(c))]:
        kap=kappa(c,k)
        rows.append(dict(c=float(c),c_fraction=str(c),mode=mode,k=k,kappa=float(kap),kappa_fraction=str(kap)))
    with data.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    assert recover(F(81,100))==1 and recover(F(9,10))==2 and recover(F(19,20))==5
    assert kappa(F(81,100),1)==F(361,16561)
    print(json.dumps(dict(status='EXACT_DERIVED_GRID_CREATED',rows=len(rows),
        missing_values=0,groups={'fixed_k1':601,'homogeneous_qualified':601},
        empirical_samples=False,range_c=[0.8,0.95],maximum_k=5)))
    raise SystemExit

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
skill_scripts=Path('C:/Users/ykw/.codex/skills/scipilot-figure-skill/scripts')
sys.path.insert(0,str(skill_scripts))
from visual_qa import audit_layout,render_preview

with data.open(encoding='utf-8',newline='') as stream:
    rows=list(csv.DictReader(stream))
assert len(rows)==1202
plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.labelsize':8,
    'xtick.labelsize':8,'ytick.labelsize':8,'axes.linewidth':.7,
    'axes.spines.top':False,'axes.spines.right':False,'legend.frameon':False,
    'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
    'mathtext.fontset':'dejavusans'})
fig,axs=plt.subplots(1,2,figsize=(7.16,3.1))
fig.subplots_adjust(left=.09,right=.985,bottom=.19,top=.86,wspace=.34)
blue='#0072B2'; orange='#D55E00'
fixed=[r for r in rows if r['mode']=='fixed_k1']
axs[0].plot([float(r['c']) for r in fixed],[float(r['kappa']) for r in fixed],
    color=blue,ls='--',lw=1.2,label=r'Fixed $k=1$')
def kfloat(c,k):
    aa=sum(c**j for j in range(k+1));bb=sum(c**(2*j) for j in range(k+1))
    return (k+1)-aa*aa/bb

endpoints=[]
for k in range(1,6):
    left=.8 if k==1 else float(gamma)**(1/(k-1))
    right=min(.95,float(gamma)**(1/k))
    if left>right: continue
    # Fixed declared k on each segment, never log/ceil at irrational ties.
    xs=[left+(right-left)*i/160 for i in range(161)]
    axs[0].plot(xs,[kfloat(x,k) for x in xs],color=orange,lw=1.25,
        label=r'Qualified $k(c)$' if k==1 else None)
    axs[1].plot([left,right],[k,k],color='0.2',lw=1.25)
    for ax,y in [(axs[0],kfloat(right,k)),(axs[1],k)]:
        ax.plot(right,y,'o',ms=3.1,color=orange if ax is axs[0] else '0.2')
    if k>1:
        axs[0].plot(left,kfloat(left,k),'o',ms=3.1,mfc='white',mec=orange,mew=.8)
        axs[1].plot(left,k,'o',ms=3.1,mfc='white',mec='0.2',mew=.8)
    endpoints.append(dict(k=k,left=left,right=right,right_closed=True,left_closed=(k==1),
                          kappa_right_display=kfloat(right,k)))

bestc=F(81,100);bestkap=kappa(bestc,1)
axs[0].plot(float(bestc),float(bestkap),'s',ms=4,color='black',zorder=4)
axs[0].text(.803,.007,r'$c_*=0.81$',fontsize=8,color='black')
axs[0].set_ylabel(r'Constant-input gap penalty $\kappa$')
axs[0].set_ylim(0,.098)
axs[0].set_yticks([0,.02,.04,.06,.08])
axs[0].legend(loc='upper right',fontsize=8,handlelength=2)
axs[1].set_ylabel(r'Excluded slots $k(c)$')
axs[1].set_ylim(.6,5.5)
axs[1].set_yticks([1,2,3,4,5])
for i,ax in enumerate(axs):
    ax.set_xlim(.798,.952)
    ax.set_xticks([.80,.85,.90,.95])
    ax.set_xlabel(r'Closed-loop parameter $c$')
    ax.tick_params(direction='out',length=3,width=.7)
    ax.grid(axis='y',color='0.92',lw=.55)
    ax.set_axisbelow(True)
    bb=ax.get_position()
    fig.text(bb.x0, .915, f'({chr(97+i)})',fontweight='bold',fontsize=8,va='center')
fig.text(.50,.970,r'Homogeneous qualification: $c^s\leq0.81$, $k=s$',
         ha='center',va='center',fontsize=8)

preview=OUT/'control_settling_figure_preview_v1.png'
render_preview(fig,str(preview),dpi=180)
issues=audit_layout(fig)
qa=dict(status='MACHINE_LAYOUT_PASS' if not any(s=='FAIL' for s,m in issues) else 'FAIL',
        issues=issues,figure_size_inches=[7.16,3.1],min_font_pt=8,
        analytical_not_empirical=True,endpoint_display_approximate=True,
        exact_optimum_fraction=dict(c=str(bestc),kappa=str(bestkap)),endpoints=endpoints)
(OUT/'control_settling_figure_qa_v1.json').write_text(json.dumps(qa,indent=2)+'\n',encoding='utf-8')
with Image.open(preview) as img:
    img.convert('L').save(OUT/'control_settling_figure_grayscale_v1.png')
if args.export:
    assert not any(s=='FAIL' for s,m in issues)
    for ext in ['pdf','svg']:
        fig.savefig(OUT/f'control_settling_figure_v1.{ext}')
    fig.savefig(OUT/'control_settling_figure_v1.png',dpi=600)
print(json.dumps(qa,indent=2))
