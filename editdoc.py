from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from copy import deepcopy
src=r'C:\Users\12488\Desktop\第三版模板-葛宣成.docx'; out=r'C:\Users\12488\Desktop\第三版模板-葛宣成_已修改.docx'
d=Document(src)
# helpers
def insert_after(par, text, style='Normal'):
    new_p=OxmlElement('w:p'); par._p.addnext(new_p); np=Paragraph(new_p, par._parent)
    np.style=style; np.add_run(text); return np

def find(text, start=0):
    for i,p in enumerate(d.paragraphs[start:],start):
        if text in p.text: return p
    return None
# center images in chapter 2 range based on paragraphs containing drawings
for i,p in enumerate(d.paragraphs):
    if 110 <= i <= 123:
        if p._p.xpath('.//w:drawing') or p._p.xpath('.//w:pict'):
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
# enrich chapter 2 after key headings
p=find('总体技术方案')
if p:
    last=p
    texts=[
    '本研究总体方案围绕“多源数据解析—模态特征提取—统一语义表征—事件级上下文关联—结构化条目输出”的链路组织。输入包括文本、表格、图片和时间序列等异构资料，先按来源、章节、页码和对象类型建立可追溯的原始证据单元，再在统一语义空间中完成跨模态对齐。',
    'Visio流程图所表达的核心关系可归纳为四个层次：多源数据经过解析后形成候选对象；文本、视觉和时序编码器分别提取语义、空间结构与变化趋势；共享表示层完成对象和事件的对齐；关联结果通过关系依据核对、关联状态表达、来源依据保留和结构化关联条目实现可解释输出。',
    '为保证研究结果可复核，每个关联条目同时保存原文片段、图片或表格引用、章节位置、时间窗口、关系类型、证据强度和处理状态。系统先扩大候选召回，再结合文档归属、对象类型、事件锚点和语义相似度进行筛选，最后由规则约束和人工复核共同确认。',
    '该方案兼顾研究效率与工程可用性：批处理阶段完成格式统一和特征缓存，推理阶段只对候选窗口进行精细匹配，验证阶段输出可追溯证据链。这样既能支持多模态上下文关联，也为后续一致性校验提供粒度明确、来源清晰的检测对象。']
    for t in texts: last=insert_after(last,t)
p=find('关键技术路线')
if p:
    last=p
    for t in ['关键技术路线按“解析、编码、对齐、关联、核对、输出”六步实施。解析阶段识别章节层级、表格行、图片锚点和 Visio 图元文本；编码阶段分别生成文本语义向量、视觉结构特征和时间序列表示；对齐阶段以对象、事件和时间窗口为共同锚点建立候选对应。','关联阶段显式区分“同一对象”“同一事件”“同一来源”和“支持关系”，避免仅凭位置相邻或关键词重复作出确认。核对阶段检查关系依据是否完整、来源是否存在、状态是否明确，并将低置信度结果保留为待复核项。输出阶段形成结构化条目，为一致性检测提供统一输入。']:
        last=insert_after(last,t)
# test sections
p=find('场景1（葛宣城）')
if p:
    last=p
    last=insert_after(last,'本场景验证多源资料在统一对象粒度下的聚合能力，重点观察文本描述、图片、表格行和来源位置能否形成可追溯的关联条目。')
    last=insert_after(last,'1.1.1.1 数据收集与样本分析','Heading 4')
    last=insert_after(last,'选取项目资料中的需求正文、接口说明、流程图片、Visio图和相关表格作为样本，按文档、章节、页码和资料类型建立索引。样本覆盖对象描述、事件步骤、参数约束和来源依据四类内容；对文本进行段落切分，对图片提取图题和邻接文字，对表格保留表头、行号及关键字段，并记录同一对象在不同位置的候选出现。')
    last=insert_after(last,'1.1.1.2 试验设计与实施过程','Heading 4')
    last=insert_after(last,'首先运行文档解析模块，生成章节树、对象候选和证据单元；其次分别计算文本语义、图片邻接、表格字段和时间窗口特征，形成候选关联对；然后依据对象名称、事件锚点、来源位置和关系类型进行综合裁决。对裁决结果逐条检查来源是否可回溯、关系依据是否明确、关联状态是否完整，并保存结构化条目和待复核项。')
# fix scene 2 label
for p in d.paragraphs:
    if 'AA场景2' in p.text: p.text=p.text.replace('AA场景2','场景2')
# add content to scene headings 2-5
scene_data={
'场景2（葛宣城）':'验证跨章节同一参数和功能描述的关联，重点检查正文、接口表和测试记录之间的对象一致性。实施时按参数名、单位、取值范围和章节来源生成候选组，人工核对证据链后输出关联状态。',
'场景3（严世军）':'验证事件级上下文关联能力，重点检查前置条件、处理步骤、输出结果和异常分支能否按时间顺序组织。实施时以事件锚点划分窗口，结合关系依据和来源位置完成事件链重建。',
'场景4（陈翔宇）':'验证多模态特征提取与语义对齐能力，重点检查流程图、界面截图和文字步骤对同一操作的共同支持。实施时先提取图元文本和空间关系，再与邻接段落、表格行进行联合匹配并保留证据。',
'场景5（葛宣城）':'验证结构化关联条目的追溯和复核能力，重点检查条目是否包含完整来源、语义角色、关联状态和置信信息。实施时导出条目清单，随机抽取结果回看原文和图片，记录确认、待复核及需修正项。'}
for key,txt in scene_data.items():
    p=find(key)
    if p: insert_after(p,txt)
d.save(out)
print(out)
