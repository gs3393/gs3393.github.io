"""Build original diffusion diagrams using only the Python standard library."""
from pathlib import Path
import base64
import html
import math
import random
import struct
import zlib

ROOT = Path(__file__).resolve().parent
INK, MUTED, TEAL, ORANGE, BLUE = "#223942", "#61747e", "#187c80", "#bd633e", "#426fa4"

def text(x, y, value, size=22, fill=INK, anchor="start", weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(value))}</text>'

def line(x1, y1, x2, y2, color=MUTED, width=2, arrow=False, dash=False):
    extra = f' marker-end="url(#{color[1:]})"' if arrow else ""
    extra += ' stroke-dasharray="7 6"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{extra}/>'

def box(x, y, w, h, labels, fill="#edf5f5", stroke="#d3e1e4", size=20):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}"/>'
    for i, label in enumerate(labels):
        s += text(x+w/2, y+h/2+(i-(len(labels)-1)/2)*27+7, label, size, anchor="middle")
    return s

def svg(name, width, height, title, parts):
    markers = "".join(f'<marker id="{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>' for c in [MUTED,TEAL,ORANGE,BLUE])
    result = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{html.escape(title)}</title><defs>{markers}</defs><rect width="100%" height="100%" fill="white"/><g font-family="Arial, Helvetica, sans-serif">{"".join(parts)}</g></svg>'
    (ROOT/name).write_text(result, encoding="utf-8")

def png_url(pixels, side):
    raw = bytearray()
    for row in range(side):
        raw.append(0)
        for col in range(side):
            for value in pixels[(row*side+col)*3:(row*side+col+1)*3]:
                raw.append(max(0,min(255,round((value+1)*127.5))))
    def chunk(kind,data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    blob=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",side,side,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b"")
    return "data:image/png;base64,"+base64.b64encode(blob).decode()

def noising():
    side=72
    pixels=[]
    for yy in range(side):
        for xx in range(side):
            x,y=xx/(side-1),yy/(side-1)
            rgb=(110+35*y,175+25*y,219+15*y)
            if (x-.78)**2+(y-.2)**2<.085**2:
                rgb=(247,208,104)
            mountain=.25+abs(x-.39)*.85
            if y>mountain:
                rgb=(72,109,119)
                if y<mountain+.10 and .22<x<.54:
                    rgb=(222,233,231)
            if y>.66:
                rgb=(55+20*(y-.66),133,151)
            if y>.83+.035*math.sin(x*18):
                rgb=(61,93,73)
            for center in [.10,.19,.88]:
                if .52<y<.9 and abs(x-center)<(y-.52)*.13:
                    rgb=(26,65,52)
            pixels.extend((v/127.5-1 for v in rgb))
    stages={0:png_url(pixels,side)}
    rng=random.Random(3393)
    selected=[0,100,250,500,750,1000]
    for t in range(1,1001):
        beta=.0001+(.02-.0001)*(t-1)/999
        signal,noise=math.sqrt(1-beta),math.sqrt(beta)
        pixels=[signal*v+noise*rng.gauss(0,1) for v in pixels]
        if t in selected:
            stages[t]=png_url(pixels,side)
    parts=[text(28,36,"Known corruption process",25,TEAL,weight=600),line(365,29,1010,29,TEAL,2.5,True)]
    for i,t in enumerate(selected):
        x=28+i*170
        parts.append(f'<image x="{x}" y="70" width="148" height="148" href="{stages[t]}"/>')
        parts.append(text(x+74,252,f"t = {t}",21,anchor="middle"))
        if i<5:
            parts.append(line(x+151,144,x+166,144,MUTED,2,True))
    parts += [line(1004,292,36,292,ORANGE,2.5,True),text(530,332,"Direction of learned generation",23,ORANGE,"middle"),text(530,373,"Forward samples shown above; the reverse arrow is conceptual.",18,MUTED,"middle")]
    svg("noising-process.svg",1060,400,"A computed forward noising trajectory and the direction of generation",parts)

def plot_points(values,x0,y0,w,h,xmin,xmax,ymin,ymax,color,width=3):
    coords=" ".join(f"{x0+(x-xmin)/(xmax-xmin)*w:.2f},{y0+h-(y-ymin)/(ymax-ymin)*h:.2f}" for x,y in values)
    return f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>'

def axes(parts,x,y,w,h,x_ticks,y_ticks,xrange,yrange):
    for val,label in y_ticks:
        py=y+h-(val-yrange[0])/(yrange[1]-yrange[0])*h
        parts += [line(x,py,x+w,py,"#e4ebee",1),text(x-13,py+6,label,17,MUTED,"end")]
    parts += [line(x,y,x,y+h,MUTED,1.5),line(x,y+h,x+w,y+h,MUTED,1.5)]
    for val,label in x_ticks:
        px=x+(val-xrange[0])/(xrange[1]-xrange[0])*w
        parts += [text(px,y+h+29,label,17,MUTED,"middle")]

def schedule():
    beta,signal,noise=[],[(0,1)],[(0,0)]
    abar=1.
    for t in range(1,1001):
        b=.0001+(.02-.0001)*(t-1)/999
        abar*=1-b
        beta.append((t,b))
        signal.append((t,math.sqrt(abar)))
        noise.append((t,math.sqrt(1-abar)))
    parts=[text(88,34,"One step",25,weight=600),text(605,34,"Accumulated over many steps",25,weight=600)]
    axes(parts,88,70,375,255,[(0,"0"),(500,"500"),(1000,"1000")],[(0,"0"),(.01,"0.01"),(.02,"0.02")],(0,1000),(0,.02))
    axes(parts,605,70,375,255,[(0,"0"),(500,"500"),(1000,"1000")],[(0,"0"),(.5,"0.5"),(1,"1")],(0,1000),(0,1))
    parts += [plot_points(beta,88,70,375,255,0,1000,0,.02,BLUE),plot_points(signal,605,70,375,255,0,1000,0,1,TEAL),plot_points(noise,605,70,375,255,0,1000,0,1,ORANGE)]
    parts += [text(278,390,"Forward step t",19,MUTED,"middle"),text(792,390,"Forward step t",19,MUTED,"middle"),text(103,103,"βₜ: fresh noise variance",20,BLUE),text(760,158,"σₜ: noise amplitude",20,ORANGE),text(627,282,"aₜ: signal amplitude",20,TEAL)]
    svg("noise-schedule.svg",1060,415,"The DDPM linear beta schedule and its cumulative amplitudes",parts)
    print(f"alpha_bar[1000]={abar:.12g}; signal={math.sqrt(abar):.12g}")

def score():
    density,gradient=[],[]
    means,variance=[-1.6,0,1.6],.36
    for i in range(501):
        x=-3.2+6.4*i/500
        comps=[1/3/math.sqrt(2*math.pi*variance)*math.exp(-(x-mu)**2/(2*variance)) for mu in means]
        q=sum(comps)
        s=sum(c*-(x-mu)/variance for c,mu in zip(comps,means))/q
        density.append((x,q));gradient.append((x,s))
    parts=[text(65,28,"Density qₜ(x)",21,weight=600),text(65,274,"Score: slope of log density",21,weight=600)]
    ticks=[(-3,"−3"),(-1,"−1"),(1,"1"),(3,"3")]
    axes(parts,65,65,565,140,ticks,[(0,"0"),(.15,".15"),(.3,".30")],(-3.2,3.2),(0,.3))
    axes(parts,65,312,565,145,ticks,[(-5,"−5"),(0,"0"),(5,"5")],(-3.2,3.2),(-5,5))
    px=65+4.2/6.4*565
    parts += [plot_points(density,65,65,565,140,-3.2,3.2,0,.3,TEAL),plot_points(gradient,65,312,565,145,-3.2,3.2,-5,5,ORANGE)]
    parts += [line(px,65,px,205,BLUE,1.5,dash=True),line(px,312,px,457,BLUE,1.5,dash=True),text(px+10,50,"Observed x = 1",16,BLUE),text(px+10,300,"Score ≈ +0.37",16,BLUE),text(348,516,"Same toy dataset: aₜ = 0.8, σₜ = 0.6",18,MUTED,"middle")]
    svg("score-field.svg",680,540,"Density and score for the three-original toy dataset",parts)

def mixtures():
    colors=[BLUE,TEAL,ORANGE]
    for name,title,a in [("low","Low noise",.96),("middle","Intermediate noise",.8),("high","High noise",.1)]:
        sigma=math.sqrt(1-a*a)
        values=[[],[],[]];total=[]
        for i in range(401):
            x=-3.5+7*i/400
            weights=[math.exp(-.5*((x-a*z)/sigma)**2)/(3*sigma*math.sqrt(2*math.pi)) for z in [-2,0,2]]
            for curve,y in zip(values,weights): curve.append((x,y))
            total.append((x,sum(weights)))
        parts=[text(32,30,title,20,weight=600),text(32,58,f"aₜ = {a:g}, σₜ ≈ {sigma:.2f}",16,MUTED)]
        axes(parts,40,88,280,150,[(-3,"−3"),(0,"0"),(3,"3")],[(0,"0"),(.3,".3"),(.6,".6")],(-3.5,3.5),(0,.6))
        for curve,color in zip(values,colors): parts.append(plot_points(curve,40,88,280,150,-3.5,3.5,0,.6,color,1.8))
        parts.append(plot_points(total,40,88,280,150,-3.5,3.5,0,.6,INK,3))
        parts += [text(180,287,"Noisy sample coordinate x",16,MUTED,"middle")]
        svg(f"mixture-{name}.svg",350,310,f"Three Gaussian components and their mixture at {title.lower()}",parts)

def reverse_step():
    values=[[],[]]
    for i in range(401):
        x=-2.8+5.6*i/400
        for curve,sd in zip(values,[.85,.45]): curve.append((x,math.exp(-.5*(x/sd)**2)/(sd*math.sqrt(2*math.pi))))
    parts=[text(48,32,"One reverse transition",22,weight=600)]
    axes(parts,60,75,560,190,[(-2,""),(0,"μθ"),(2,"")],[(0,"0"),(.5,".5"),(1,"1")],(-2.8,2.8),(0,1))
    parts += [plot_points(values[0],60,75,560,190,-2.8,2.8,0,1,TEAL,3),plot_points(values[1],60,75,560,190,-2.8,2.8,0,1,BLUE,2)]
    parts += [text(465,90,"Smaller variance",16,BLUE),text(465,116,"Larger variance",16,TEAL),line(340,85,340,260,MUTED,1,dash=True)]
    parts += [line(340,320,430,320,ORANGE,2,True),text(385,349,"√rₜ η",18,ORANGE,"middle"),line(430,263,430,285,ORANGE,2),text(445,291,"Sampled xₜ₋₁",17,ORANGE),text(340,389,"Noise prediction sets the center; variance sets the spread.",17,MUTED,"middle")]
    svg("reverse-step.svg",680,415,"Reverse transition mean, variance, and a sampled next state",parts)

def cfg_evaluations():
    parts=[text(24,30,"Training: learn both condition settings",22,weight=600)]
    parts += [box(24,58,190,75,["Label c", "or null (randomly)"],size=17),line(220,95,283,95,MUTED,2,True),box(290,58,180,75,["One denoiser", "input: xₜ, t, condition"],size=16),line(475,95,538,95,MUTED,2,True),box(545,58,190,75,["Noise prediction", "MSE with known ε"],size=17)]
    parts += [text(24,195,"Inference: compare at the same state",22,weight=600),box(24,305,150,70,["Same xₜ, t"],size=19)]
    parts += [f'<path d="M 178 340 H 209 V 263 H 245" fill="none" stroke="{TEAL}" stroke-width="2" marker-end="url(#{TEAL[1:]})"/>',f'<path d="M 178 340 H 209 V 410 H 245" fill="none" stroke="{BLUE}" stroke-width="2" marker-end="url(#{BLUE[1:]})"/>']
    parts += [box(253,228,230,70,["Denoiser with c", "conditional prediction"],size=18),box(253,375,230,70,["Denoiser with null", "unconditional prediction"],size=18),text(367,337,"Shared weights",17,MUTED,"middle")]
    parts += [f'<path d="M 488 263 H 518 V 326 H 550" fill="none" stroke="{TEAL}" stroke-width="2" marker-end="url(#{TEAL[1:]})"/>',f'<path d="M 488 410 H 518 V 353 H 550" fill="none" stroke="{BLUE}" stroke-width="2" marker-end="url(#{BLUE[1:]})"/>',box(558,305,178,70,["CFG combination", "guided prediction"],"#f9f1e9",size=17),line(647,381,647,455,ORANGE,2,True),box(558,463,178,60,["Sampler → xₜ₋₁"],size=17)]
    svg("cfg-evaluations.svg",760,548,"Condition dropout during training and two shared-weight evaluations during inference",parts)

def cfg():
    origin=(105,361);uncond=(355,280);cond=(535,190);guided=(715,100)
    parts=[text(40,40,"Same input, same noise level — different predictions",24,weight=600)]
    for dest,color in [(guided,ORANGE),(cond,TEAL),(uncond,BLUE)]:
        parts.append(line(*origin,*dest,color,3,True))
        parts.append(f'<circle cx="{dest[0]}" cy="{dest[1]}" r="5" fill="{color}"/>')
    parts += [line(*uncond,*cond,MUTED,2,True,True),line(*cond,*guided,MUTED,2,True,True)]
    parts += [text(80,395,"0",21),text(375,302,"Unconditional, γ = 0",21,BLUE),text(558,209,"Conditional, γ = 1",21,TEAL),text(735,106,"Guided, γ = 2",22,ORANGE),text(714,259,"One difference",18,MUTED),text(714,283,"beyond conditional",18,MUTED)]
    parts += [box(40,422,975,63,["guided = unconditional + γ × (conditional − unconditional)"],"#f4f7f8",size=22)]
    svg("cfg-vectors.svg",1060,513,"Classifier-free guidance extrapolates prediction vectors",parts)

def dit():
    parts=[text(30,35,"Latent diffusion with a DiT denoiser",25,weight=600)]
    blocks=[(24,90,110,82,["Image","256 × 256"]),(162,90,117,82,["Frozen","VAE encoder"]),(307,90,140,82,["Noisy latent","32 × 32 × 4"]),(475,90,130,82,["Patch","projection"]),(633,90,145,82,["DiT blocks","256 × D"]),(806,90,227,82,["Unpatchify","noise + variance params"])]
    for x,y,w,h,labels in blocks:
        parts.append(box(x,y,w,h,labels,size=18))
    for i in range(len(blocks)-1):
        x,y,w,h,_=blocks[i];nx=blocks[i+1][0]
        parts.append(line(x+w+3,y+h/2,nx-5,y+h/2,MUTED,2,True))
    parts += [text(209,205,"z₀: 32 × 32 × 4",15,MUTED,"middle"),text(377,232,"zₜ = aₜ z₀ + σₜ ε",18,TEAL,"middle"),text(551,205,"P = 2; 16 values → D",15,MUTED,"middle"),text(920,209,"Spatial output: 32 × 32 × 8",17,MUTED,"middle")]
    parts += [text(30,260,"Inside one",22,weight=600),text(30,289,"adaLN-Zero block",22,weight=600),box(340,247,280,62,["timestep + class context"],"#f9f1e9",size=20),line(624,278,687,278,ORANGE,2,True),box(695,247,337,62,["shift, scale, gate × 2 branches"],"#f9f1e9",size=18)]
    for y,left,op,right,gate in [(361,"h","Attention","h′","g_A"),(529,"h′","MLP","h_out","g_M")]:
        parts += [text(39,y+39,left,22,weight=600),line(87,y+31,147,y+31,MUTED,2,True),box(153,y,220,64,["LayerNorm + modulation"],size=18),line(379,y+31,435,y+31,MUTED,2,True),box(443,y,178,64,[op],size=20),line(627,y+31,685,y+31,MUTED,2,True),box(693,y,117,64,["× "+gate],"#f9f1e9",size=20),line(815,y+31,887,y+31,MUTED,2,True),box(895,y,53,64,["+"],size=25),line(953,y+31,993,y+31,MUTED,2,True),text(1000,y+38,right,18)]
        parts += [f'<path d="M 110 {y+31} V {y+105} H 921 V {y+70}" fill="none" stroke="{BLUE}" stroke-width="2" marker-end="url(#{BLUE[1:]})"/>',text(525,y+96,"Residual path",17,BLUE,"middle")]
    parts += [text(32,698,"Zero-initialized gates make each residual block start as the identity.",20,MUTED)]
    svg("dit-architecture.svg",1060,725,"DiT latent data path and the two branches of an adaLN-Zero block",parts)

if __name__=="__main__":
    noising()
    schedule()
    score()
    mixtures()
    reverse_step()
    cfg_evaluations()
    cfg()
    dit()
    print("Wrote ten original SVG figures.")
