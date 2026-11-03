from docx import Document
p=r'C:\Users\12488\Desktop\第三版模板-葛宣成.docx'; d=Document(p)
with open(r'C:\Users\12488\Desktop\data_clean\outline.txt','w',encoding='utf-8') as f:
 for i,p in enumerate(d.paragraphs):
  t=p.text.strip()
  if t and (p.style.name.startswith('Heading') or t.startswith('第') or t.startswith('1.1')): f.write(f'{i}\t{p.style.name}\t{t}\n')
