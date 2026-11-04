from docx import Document
p=r'C:\Users\12488\Desktop\data_clean\modified.docx'; d=Document(p)
for key in ['总体技术方案','关键技术路线','场景1（葛宣城）','场景2（葛宣城）','场景3（严世军）','场景4（陈翔宇）','场景5（葛宣城）']:
 print(key, sum(1 for x in d.paragraphs if key in x.text))
print('inline_shapes',len(d.inline_shapes))
