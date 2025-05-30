from flask import Blueprint, render_template, request, jsonify, send_file
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .text_qa import get_answer
from .image_qa import visual_question_answer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import jieba.posseg as pseg
from app.gpt_summary import generate_gpt_summary
from app.text_mining import perform_text_mining
import os
import pdfplumber
from docx import Document
import zipfile
import uuid

# 创建蓝图
bp = Blueprint('main', __name__)

# 读取知识库CSV文件（知识库路径根据实际情况修改）
knowledge_df = pd.read_csv('app/data/knowledge.csv')

# 读取停用词（如果有停用词文件）
stopwords = []
try:
    with open('app/data/stopwords.txt', 'r', encoding='utf-8') as f:
        stopwords = f.read().splitlines()
except FileNotFoundError:
    print("停用词文件未找到，使用默认停用词列表。")

# 使用TF-IDF提取特征
vectorizer = TfidfVectorizer(stop_words=stopwords if stopwords else 'english')
X = vectorizer.fit_transform(knowledge_df['question'])

# 首页路由
@bp.route('/')
def index():
    return render_template('index.html')

# 问答系统路由
@bp.route('/query', methods=['GET', 'POST'])
def query():
    # 获取用户输入
    user_input = request.args.get('question') or request.json.get('question')
    if not user_input:
        return jsonify({"answer": "请输入问题!"})
    
    # 使用语义模型计算答案
    answer = get_answer(user_input)
    return jsonify({"answer": answer})

@bp.route('/visual_qa', methods=['POST'])
def visual_qa():
    image_file = request.files.get('image')
    user_question = request.form.get('question', '')

    if not image_file or not user_question.strip():
        return jsonify({'error': '请上传图片并输入问题'}), 400

    try:
        answer = visual_question_answer(image_file, user_question)
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': f'处理失败：{e}'}), 500

def extract_text_from_pdf(file):
    # pdfplumber 需要文件是可读取的流对象
    with pdfplumber.open(file) as pdf:
        texts = [page.extract_text() or '' for page in pdf.pages]
    return '\n'.join(texts)

def extract_text_from_docx(file):
    doc = Document(file)
    texts = [para.text for para in doc.paragraphs]
    return '\n'.join(texts)

# 文档处理功能路由（上传文件、词性标注、实体识别等）
@bp.route('/upload_document', methods=['POST'])
def upload_document():
    file = request.files.get('file')
    text = request.form.get('text', '')
    mode = request.form.get('type', '')

    # 先处理 zip 模式，专门处理上传的 zip 文件
    if mode == 'zip':
        if not file or not file.filename.endswith('.zip'):
            return jsonify({"result": "请上传 zip 格式的文件。"})
        
        upload_folder = os.path.join('app/data/uploads', str(uuid.uuid4()))
        os.makedirs(upload_folder, exist_ok=True)

        zip_path = os.path.join(upload_folder, file.filename)
        file.save(zip_path)

        # 这里假设 perform_text_mining 函数接收的是 zip 文件路径
        try:
            result_html = perform_text_mining(zip_path)
        except Exception as e:
            return jsonify({"result": f"文本挖掘失败: {str(e)}"})

        return jsonify({"result": result_html})

    # 非 zip 模式，先解析上传的文件内容为文本
    if file:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()

        if ext == '.txt':
            text = file.read().decode('utf-8', errors='ignore')
        elif ext == '.pdf':
            try:
                text = extract_text_from_pdf(file)
            except Exception as e:
                return jsonify({"result": f"PDF 解析失败: {str(e)}"})
        elif ext in ['.doc', '.docx']:
            try:
                text = extract_text_from_docx(file)
            except Exception as e:
                return jsonify({"result": f"DOCX 解析失败: {str(e)}"})
        else:
            return jsonify({"result": "不支持的文件类型，仅支持 txt、pdf、doc、docx"})

    if not text.strip():
        return jsonify({"result": "请提供有效文本"})

    # 根据不同模式执行不同文本处理
    if mode == 'pos':
        words = pseg.cut(text)
        pos_color_map = {
            'n': "#6fadf3",   # 名词
            'v': "#7cf667",   # 动词
            'a': "#b041f5",   # 形容词
            'm': "#eeba11",   # 数量词
            'd': "#73c1cd",   # 副词
            'r': "#fca644",   # 代词
            'c': "#f54545"    # 连词
        }
        result_parts = []
        for word in words:
            color = pos_color_map.get(word.flag[0], '#eeeeee')
            html = f'<span style="background:{color}; padding:2px 5px; margin:1px; border-radius:5px;">{word.word}</span>'
            result_parts.append(html)
        result = ''.join(result_parts)
        return jsonify({"result": result})

    elif mode == 'ner':
        words = pseg.cut(text)
        entity_color_map = {
            'nr': "#ec0808",  # 人名
            'ns': "#15b7ed",  # 地名
            'nt': "#10e810"   # 机构名
        }
        result_parts = []
        for word in words:
            color = entity_color_map.get(word.flag, None)
            if color:
                html = f'<span style="background:{color}; padding:2px 5px; margin:1px; border-radius:5px;">{word.word}</span>'
            else:
                html = word.word
            result_parts.append(html)
        result = ' '.join(result_parts)
        return jsonify({"result": result})

    elif mode == 'summary':
        try:
            summary = generate_gpt_summary(text)
            if summary.startswith("调用 GPT 出错"):
                return jsonify({"result": summary})
            result = f"<b>摘要：</b><br>{summary}"
            return jsonify({"result": result})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"result": f"摘要生成失败: {str(e)}"})

    else:
        return jsonify({"result": "未知的处理类型"})




@bp.route('/download_result', methods=['POST'])
def download_result():
    text = request.form.get('text', '')
    mode = request.form.get('type', '')

    from io import BytesIO
    from flask import send_file

    if not text.strip():
        return jsonify({"error": "文本不能为空"}), 400

    filename = f"{mode}_result.txt"
    buffer = BytesIO()
    buffer.write(text.encode('utf-8'))
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/plain')

@bp.route('/download_zip_images', methods=['GET'])
def download_zip_images():
    folder_name = request.args.get('folder')
    if not folder_name:
        return jsonify({"error": "缺少 folder 参数"}), 400

    # 图片所在目录，和你生成图的路径保持一致
    image_folder = os.path.join('app/static/uploads', folder_name)
    if not os.path.exists(image_folder):
        return jsonify({"error": "文件夹不存在"}), 404

    zip_path = os.path.join('app/static/uploads', f"{folder_name}.zip")

    # 如果zip不存在则重新打包
    if not os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for root, dirs, files in os.walk(image_folder):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filepath = os.path.join(root, file)
                        arcname = os.path.relpath(filepath, image_folder)
                        zf.write(filepath, arcname)

    return send_file(zip_path, as_attachment=True)