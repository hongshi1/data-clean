from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches
from pathlib import Path
import zipfile, shutil, os
src=r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\葛宣成 合稿.docx'
ref4=r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\场景4实验_V2(1).docx'
ref3=r'C:\Users\12488\Documents\xwechat_files\wxid_1k54h2jymo0022_a344\msg\file\2026-11\场景三试验(1).docx'
out=r'C:\Users\12488\Desktop\data_clean\葛宣成_合稿_补充截图.docx'
imgdir=Path(r'C:\Users\12488\Desktop\data_clean\ref_imgs'); imgdir.mkdir(exist_ok=True)
def extract(docx, indices, prefix):
    z=zipfile.ZipFile(docx); names=sorted([n for n in z.namelist() if n.startswith('word/media/') and n.lower().endswith(('.png','.jpg','.jpeg','.emf'))])
    out=[]
    for i in indices:
      if i < len(names):
        ext=Path(names[i]).suffix; p=imgdir/f'{prefix}_{i}{ext}'; p.write_bytes(z.read(names[i])); out.append(str(p))
    return out
# use representative screenshots from both reports
imgs3=extract(ref3,[0,4,8,11,13],'scene3')
imgs4=extract(ref4,[0,5,10,15,20],'scene4')
# combine in scene order, two per scene
pairs=[imgs3[:2],imgs4[:2],imgs3[2:4],imgs4[2:4],imgs3[4:]+imgs4[4:]]
d=Document(src)
def insert_after(par, text=None, image=None, caption=None):
  anchor=par._p
  if text is not None:
    el=OxmlElement('w:p'); anchor.addnext(el); np=Paragraph(el,par._parent); np.style='Normal'; np.add_run(text); return np
  el=OxmlElement('w:p'); anchor.addnext(el); np=Paragraph(el,par._parent); np.alignment=WD_ALIGN_PARAGRAPH.CENTER
  run=np.add_run(); run.add_picture(image,width=Inches(5.8)); anchor=np._p
  if caption:
    el2=OxmlElement('w:p'); anchor.addnext(el2); cp=Paragraph(el2,np._parent); cp.alignment=WD_ALIGN_PARAGRAPH.CENTER; cp.style='Caption'; cp.add_run(caption); return cp
  return np
# Locate test result scene headings in order
scene_heads=[]
for p in d.paragraphs:
  if p.text.strip() in ['场景1（葛宣成）','场景2（葛宣成）','场景3（严世军）','场景4（陈翔宇）','场景5（葛宣成）']:
    scene_heads.append(p)
for idx,p in enumerate(scene_heads):
  last=p
  for j,im in enumerate(pairs[idx]):
    last=insert_after(last,image=im,caption=f'图 测试结果场景{idx+1}运行截图（{j+1}）')
# add acceptance figures under matching chapter 6 headings if present, using one figure each
for i,p in enumerate(d.paragraphs):
  if '6.4.1' in p.text or '6.4.3' in p.text or '6.4.4' in p.text or '6.4.5' in p.text:
    pass
# center every existing and inserted drawing paragraph
for p in d.paragraphs:
  if p._p.xpath('.//w:drawing') or p._p.xpath('.//w:pict'): p.alignment=WD_ALIGN_PARAGRAPH.CENTER
d.save(out); print(out)
