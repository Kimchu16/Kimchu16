"""Apply bundled Minecraft textures to the existing 3D contribution renderer's SVG.
Contribution counts and geometry are preserved; materials use fixed daily count ranges.
"""
from pathlib import Path
from PIL import Image
import xml.etree.ElementTree as E
import sys
import math
import re

ROOT=Path(__file__).resolve().parents[1]
NS='http://www.w3.org/2000/svg'
E.register_namespace('',NS)
def tag(name):return '{'+NS+'}'+name

def tint(image,color):
    image=image.convert('RGBA'); out=image.copy()
    for y in range(image.height):
        for x in range(image.width):
            r,g,b,a=image.getpixel((x,y))
            out.putpixel((x,y),(r*color[0]//255,g*color[1]//255,b*color[2]//255,a))
    return out

def apply(source,destination):
    svg=E.parse(source).getroot();defs=svg.find(tag('defs'))
    if defs is None:raise ValueError('Expected bitmap patterns in contribution SVG')
    textures=ROOT/'assets/textures'
    blocks=[Image.open(textures/(name+'.png')).convert('RGBA') for name in
            ['stone','iron_block','gold_block','emerald_block','diamond_block']]
    found=0
    for p in defs.findall(tag('pattern')):
        ident=p.get('id','')
        if not ident.startswith('pattern_'):continue
        _,level,face=ident.split('_');level=int(level)
        # Preserve GitHub's five contribution levels, with diamond as the peak.
        img=blocks[level].copy()
        if level==0:img=tint(img,(130,141,150))
        if face=='left':img=tint(img,(215,215,215))
        if face=='right':img=tint(img,(175,175,175))
        p.clear();p.attrib.update({'id':ident,'width':'16','height':'16','patternUnits':'userSpaceOnUse','shape-rendering':'crispEdges'})
        # Vector pixels make textures self-contained in GitHub's SVG image context.
        for y in range(16):
            for x in range(16):
                r,g,b,a=img.getpixel((x,y))
                if a:E.SubElement(p,tag('rect'),{'x':str(x),'y':str(y),'width':'1','height':'1','fill':f'#{r:02x}{g:02x}{b:02x}'})
        found+=1
    if found!=15:raise ValueError(f'Expected 15 face patterns, found {found}')
    # Keep the tool's calendar group; omit unrelated radar/language charts.
    groups=svg.findall(tag('g'))
    if not groups:raise ValueError('Missing contribution calendar')
    calendar=groups[0]
    # Decode the pinned upstream renderer's logarithmic bar height.
    # Fixed count thresholds keep the numeric legend accurate on future updates.
    dx=float(svg.get('width', '1280'))/64
    for bar in calendar.findall(tag('g')):
        faces=bar.findall(tag('rect'))
        left=next((f for f in faces if '_left)' in f.get('fill','')), None)
        if left is None:continue
        scale=math.hypot(dx*0.9, dx*math.tan(math.pi/6)*0.9)/float(left.get('width'))
        count=max(0, round(20*(10**((float(left.get('height'))*scale-3)/144)-1)))
        level=0 if count==0 else 1 if count<=4 else 2 if count<=9 else 3 if count<=13 else 4
        for face in faces:
            face.set('fill',re.sub(r'pattern_\d_',f'pattern_{level}_',face.get('fill','')))
    for element in list(svg):
        if element is not defs and element is not calendar:svg.remove(element)
    svg.set('role','img');svg.set('aria-label','Minecraft blocks showing GitHub contribution activity')
    title=E.Element(tag('title'));title.text='Kimchu16 — Minecraft contribution landscape';svg.insert(0,title)
    bg=E.Element(tag('rect'),{'width':'1280','height':'850','fill':'#0d1117'});svg.insert(list(svg).index(calendar),bg)
    legend=E.SubElement(svg,tag('g'),{'font-family':'Arial, sans-serif','fill':'#c9d1d9'})
    label=E.SubElement(legend,tag('text'),{'x':'36','y':'34','font-size':'18'});label.text='CONTRIBUTIONS PER DAY'
    for level,(name,amount) in enumerate([('Stone','0'),('Iron','1-4'),('Gold','5-9'),('Emerald','10-13'),('Diamond','14+')]):
        x=36+level*238
        E.SubElement(legend,tag('rect'),{'x':str(x),'y':'52','width':'32','height':'32','fill':f'url(#pattern_{level}_top)'})
        label=E.SubElement(legend,tag('text'),{'x':str(x+43),'y':'65','font-size':'18'});label.text=name
        label=E.SubElement(legend,tag('text'),{'x':str(x+43),'y':'84','font-size':'14','fill':'#8b949e'});label.text=amount
    E.ElementTree(svg).write(destination,encoding='utf-8',xml_declaration=True)
    return len(calendar.findall(tag('g')))

if __name__=='__main__':
    source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'profile-3d-contrib/minecraft-raw.svg'
    destination=ROOT/'assets/minecraft-contributions.svg'
    print('Textured calendar elements:',apply(source,destination))
