from docx import Document
p=r'C:\Users\12488\Desktop\第三版模板-葛宣成.docx'
d=Document(p)
print('paras',len(d.paragraphs),'tables',len(d.tables),'sections',len(d.sections))
for i,para in enumerate(d.paragraphs):
 t=para.text.strip()
 if t: print(i,repr(t[:160]),'style=',para.style.name,'align=',para.alignment)
